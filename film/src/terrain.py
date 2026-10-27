"""Heightfield renderer over the real DEM: photoreal (Blue Marble albedo + atmosphere) <-> analytical map style."""
import numpy as np
import moderngl
from glcore import ctx
from geo import Geo, m_per_px, TILE, Z

VS = """
#version 430
in vec2 g;
uniform vec4 rect;          // local px x0,y0,x1,y1
uniform vec2 gamma;         // grid density warp toward focus
uniform vec2 focus;         // 0..1 focus within rect
uniform sampler2D hm;
uniform vec2 dem_size;
uniform vec2 origin;        // global px of local (0,0)
uniform float world_n;      // TILE*2^Z
uniform vec3 eye;           // camera eye local px (y = altitude px)
uniform float exag;
uniform float curv_R;       // earth radius in px (0 = flat)
uniform mat4 mvp;
out vec2 uv; out vec3 wpos; out float hm_m; out float lat;
float warp(float t, float f, float k){ float d=t-f; return f + sign(d)*pow(abs(d)/max(f*step(d,0.)+(1.-f)*step(0.,d),1e-4),k)*max(f*step(d,0.)+(1.-f)*step(0.,d),1e-4); }
void main(){
  vec2 t = vec2(warp(g.x, focus.x, gamma.x), warp(g.y, focus.y, gamma.y));
  vec2 lp = mix(rect.xy, rect.zw, t);
  uv = lp / dem_size;
  float h = textureLod(hm, vec2(uv.x, 1.0-uv.y), 0.0).r;
  hm_m = h;
  float gy = lp.y + origin.y;
  lat = atan(sinh(3.14159265*(1.0-2.0*gy/world_n)));
  float mpp = 156543.03392*cos(lat)/64.0;
  float hp = max(h, -50.0)/mpp*exag;
  vec3 p = vec3(lp.x, hp, lp.y);
  vec3 r = p - eye;
  if (curv_R > 0.0) r.y -= dot(r.xz, r.xz)/(2.0*curv_R);
  wpos = r;
  gl_Position = mvp*vec4(r,1.0);
}
"""

FS = """
#version 430
in vec2 uv; in vec3 wpos; in float hm_m; in float lat;
uniform sampler2D hm; uniform sampler2D alb; uniform sampler2D chn; uniform sampler2D lnd; uniform sampler2D rel; uniform sampler2D slp;
uniform vec2 dem_size; uniform vec2 origin; uniform float world_n;
uniform vec3 sun; uniform float exag; uniform vec3 eye;
uniform float style;        // 0 photoreal, 1 analytical map
uniform float china_lift;   // highlight china in map style
uniform float contour_a;    // contour visibility
uniform float grat_a;       // graticule visibility
uniform float haze;         // atmosphere density multiplier
uniform float alt_m;        // camera altitude meters
uniform float shadow_steps;
uniform float exposure;
uniform vec3 tint_map;
uniform float map_relief;
out vec4 frag;

vec3 srgb2lin(vec3 c){ return pow(c, vec3(2.2)); }
float H(vec2 u){ return texture(hm, vec2(u.x, 1.0-u.y)).r; }

vec3 sky(vec3 d){
  float e = d.y;
  float hz = exp(-max(e,0.0)*mix(9.0,26.0,clamp(alt_m/30000.0,0.,1.)));
  vec3 zen = mix(vec3(0.10,0.22,0.48), vec3(0.012,0.03,0.09), clamp(alt_m/30000.0,0.,1.));
  vec3 hor = vec3(0.62,0.74,0.88);
  vec3 c = mix(zen, hor, hz);
  float sd = max(dot(d, sun), 0.0);
  c += vec3(1.0,0.82,0.6)*(pow(sd, 10.0)*0.35 + pow(sd, 400.0)*4.0);
  return c;
}

void main(){
  vec2 px = uv*dem_size;
  // footprint-aware normal (avoid shimmering)
  vec2 fw = max(fwidth(px), vec2(1.0));
  float s = max(fw.x, fw.y);
  vec2 dx = vec2(s/dem_size.x, 0.0), dy = vec2(0.0, s/dem_size.y);
  float mpp = 156543.03392*cos(lat)/64.0;
  vec2 sl = texture(slp, vec2(uv.x,1.0-uv.y)).rg;
  vec3 n = normalize(vec3(-sl.x*exag, 1.0, -sl.y*exag));
  float land = texture(lnd, vec2(uv.x,1.0-uv.y)).r;
  float china = texture(chn, vec2(uv.x,1.0-uv.y)).r;
  float h = hm_m;
  float dist = length(wpos);
  vec3 vdir = wpos/dist;

  // ---------- photoreal ----------
  vec3 a = srgb2lin(texture(alb, vec2(uv.x,1.0-uv.y)).rgb);
  float snow = smoothstep(4700.0, 5600.0, h) * smoothstep(0.55, 0.85, n.y);
  a = mix(a, vec3(0.80,0.83,0.86), snow*0.55);
  float ndl = max(dot(n, sun), 0.0);
  float sh = 1.0;
  if (shadow_steps > 0.5 && ndl > 0.0){
    vec3 p = vec3(px.x, h/mpp*exag, px.y);
    vec3 sd = normalize(vec3(sun.x, sun.y, sun.z));
    float stepl = 2.0;
    for (int i=1;i<=int(shadow_steps);i++){
      vec3 q = p + sd*stepl*float(i)*float(i)*0.35;
      float hq = H(q.xz/dem_size)/mpp*exag;
      sh = min(sh, clamp(1.0 - (hq - q.y)*2.5, 0.0, 1.0));
    }
  }
  vec3 sunc = vec3(1.0,0.93,0.82)*2.6;
  vec3 amb = mix(vec3(0.05,0.07,0.10), vec3(0.18,0.24,0.34), n.y*0.5+0.5);
  vec3 photo = a*(sunc*ndl*sh + amb);
  photo = mix(vec3(0.004,0.012,0.03), photo, smoothstep(0.0,0.5,land) );
  // aerial perspective (exponential atmosphere, scale height 8 km)
  float Hs = 8000.0;
  float hc = alt_m, hp = max(h, 0.0);
  float dm = dist*mpp;
  float dh = hc - hp;
  float od = dm*(abs(dh)>1.0 ? (exp(-hp/Hs)-exp(-hc/Hs))/(dh/Hs) : exp(-hp/Hs)) * 1.4e-5 * haze;
  float fog = 1.0 - exp(-od);
  vec3 fc = sky(normalize(vec3(vdir.x, max(vdir.y,0.0)*0.2+0.02, vdir.z)));
  photo = mix(photo, fc, fog);

  // ---------- analytical map ----------
  float lod = log2(max(s,1.0));
  float shade = texture(rel, vec2(uv.x,1.0-uv.y)).r;
  float hs = textureLod(hm, vec2(uv.x,1.0-uv.y), lod+0.5).r;
  vec3 ocean = mix(vec3(0.0010,0.0016,0.0026), vec3(0.0030,0.0048,0.0072), smoothstep(-4500.0,-40.0,hs));
  vec3 ground = mix(vec3(0.0022,0.0028,0.0036), vec3(0.020,0.024,0.030), pow(shade,1.6));
  vec3 cn = mix(vec3(0.0040,0.0046,0.0056), tint_map, pow(shade,1.5));
  ground = mix(ground, cn, china*china_lift);
  float landm = smoothstep(0.25,0.75,land);
  vec3 mapc = mix(ocean, ground, landm);
  // coast glow line
  mapc += vec3(0.20,0.24,0.30)*0.02*(1.0-abs(landm*2.0-1.0));
  // contours on smoothed heights (500 m, index 2500 m)
  float hc2 = textureLod(hm, vec2(uv.x,1.0-uv.y), max(lod+0.8,0.0)).r;
  float cv = hc2/500.0; float cw = fwidth(cv);
  float cl = 1.0 - smoothstep(0.0, cw*1.1, abs(fract(cv-0.5)-0.5));
  float iv = hc2/2500.0; float iw = fwidth(iv);
  float il = 1.0 - smoothstep(0.0, iw*1.4, abs(fract(iv-0.5)-0.5));
  float cfade = clamp(1.5 - cw*6.0, 0.0, 1.0);
  mapc += vec3(0.62,0.70,0.80)*(cl*0.006 + il*0.016)*contour_a*cfade*step(1.0,hc2)*landm;
  // graticule every 5 degrees
  float lon = (px.x+origin.x)/world_n*360.0-180.0;
  float latd = degrees(lat);
  vec2 gq = vec2(lon, latd)/5.0; vec2 gwd = fwidth(gq);
  vec2 gl = 1.0 - smoothstep(vec2(0.0), gwd*1.0, abs(fract(gq-0.5)-0.5));
  mapc += vec3(0.6,0.7,0.8)*max(gl.x,gl.y)*0.010*grat_a;
  vec3 col = mix(photo, mapc, style);
  frag = vec4(col*exposure, 1.0);
}
"""

SKY_FS = """
#version 430
in vec2 uv; out vec4 frag;
uniform mat3 invrot; uniform vec2 tanfov; uniform vec3 sun; uniform float alt_m; uniform float exposure; uniform float style;
uniform float curv_drop;
vec3 sky(vec3 d){
  float e = d.y + curv_drop;
  float hz = exp(-max(e,0.0)*mix(9.0,26.0,clamp(alt_m/30000.0,0.,1.)));
  vec3 zen = mix(vec3(0.10,0.22,0.48), vec3(0.012,0.03,0.09), clamp(alt_m/30000.0,0.,1.));
  vec3 hor = vec3(0.62,0.74,0.88);
  vec3 c = mix(zen, hor, hz);
  c = mix(c, vec3(0.30,0.40,0.52), smoothstep(0.0,-0.05,e));
  float sd = max(dot(d, sun), 0.0);
  c += vec3(1.0,0.82,0.6)*(pow(sd, 10.0)*0.35 + pow(sd, 400.0)*4.0);
  return c;
}
void main(){
  vec3 d = normalize(invrot*vec3((uv.x*2.0-1.0)*tanfov.x, (uv.y*2.0-1.0)*tanfov.y, -1.0));
  vec3 c = mix(sky(d), vec3(0.006,0.008,0.011), style);
  frag = vec4(c*exposure,1.0);
}
"""

class Terrain:
    def __init__(self, geo: Geo, grid=(900, 900)):
        c = ctx()
        self.geo = geo
        h = geo.h
        self.t_h = c.texture((geo.W, geo.H), 1, np.ascontiguousarray(h[::-1]).tobytes(), dtype="f4")
        self.t_h.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR); self.t_h.build_mipmaps()
        self.t_a = c.texture((geo.W, geo.H), 3, np.ascontiguousarray(geo.albedo[::-1]).tobytes())
        self.t_a.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR); self.t_a.build_mipmaps(); self.t_a.anisotropy = 8.0
        self.t_c = c.texture((geo.W, geo.H), 1, np.ascontiguousarray(geo.china[::-1]).tobytes())
        self.t_c.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR); self.t_c.build_mipmaps()
        self.t_l = c.texture((geo.W, geo.H), 1, np.ascontiguousarray(geo.land[::-1]).tobytes())
        self.t_l.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR); self.t_l.build_mipmaps()
        self.t_r = c.texture((geo.W, geo.H), 1, np.ascontiguousarray(geo.relief[::-1]).tobytes())
        self.t_r.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR); self.t_r.build_mipmaps(); self.t_r.anisotropy = 8.0
        self.t_s = c.texture((geo.W, geo.H), 2, np.ascontiguousarray(geo.slope[::-1]).tobytes(), dtype="f2")
        self.t_s.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR); self.t_s.build_mipmaps()
        for t in (self.t_h, self.t_a, self.t_c, self.t_l, self.t_r, self.t_s):
            t.repeat_x = t.repeat_y = False
        gx, gy = grid
        xs = np.linspace(0, 1, gx, dtype="f4"); ys = np.linspace(0, 1, gy, dtype="f4")
        X, Y = np.meshgrid(xs, ys)
        v = np.stack([X, Y], -1).reshape(-1, 2)
        I = (np.arange(gy - 1)[:, None] * gx + np.arange(gx - 1)[None, :]).ravel()
        tri = np.stack([I, I + gx, I + 1, I + 1, I + gx, I + gx + 1], -1).ravel().astype("i4")
        self.prog = c.program(vertex_shader=VS, fragment_shader=FS)
        self.vao = c.vertex_array(self.prog, [(c.buffer(v.tobytes()), "2f", "g")], c.buffer(tri.tobytes()))
        from glcore import Pass
        self.skyp = Pass(SKY_FS)
        self.n = TILE * 2 ** Z

    def lat_of(self, ly):
        return float(self.geo.lonlat(0, ly)[1])

    def curv_R(self, ly):
        return 6371000.0 / m_per_px(self.lat_of(ly))

    def world(self, lon, lat, alt_m=None, exag=1.0, ground_offset_m=0.0):
        """lon/lat arrays -> world (local px, y altitude px)."""
        lx, ly = self.geo.local(lon, lat)
        lx = np.atleast_1d(lx); ly = np.atleast_1d(ly)
        mpp = m_per_px(np.atleast_1d(lat))
        if alt_m is None:
            hm = np.maximum(self.geo.height(lx, ly), -50.0)
            y = hm / mpp * exag + ground_offset_m / mpp
        else:
            y = np.broadcast_to(np.asarray(alt_m, float), lx.shape) / mpp
        return np.stack([lx, y, ly], 1)

    def curve(self, pts, cam, use=True):
        """Apply the same earth-curvature drop used in the vertex shader (for overlays)."""
        if not use:
            return pts
        R = self.curv_R(cam.eye[2])
        r = pts - cam.eye
        out = pts.copy()
        out[:, 1] -= (r[:, 0] ** 2 + r[:, 2] ** 2) / (2 * R)
        return out

    def render(self, fbo, cam, rect, sun, style=0.0, exag=1.0, curvature=True, haze=1.0, contour_a=1.0, grat_a=0.0,
               china_lift=1.0, shadow_steps=0, exposure=1.0, tint_map=(0.060, 0.066, 0.074), map_relief=6.0, focus=(0.5, 0.5), gamma=(1.0, 1.0), sky=True):
        c = ctx()
        fbo.use()
        fbo.clear(0, 0, 0, 1, depth=1.0)
        alt_m = cam.eye[1] * m_per_px(self.lat_of(cam.eye[2]))
        sunv = np.asarray(sun, float); sunv /= np.linalg.norm(sunv)
        if sky:
            R = cam.R[:3, :3]
            th = np.tan(np.radians(cam.fov) / 2)
            self.skyp.run(fbo, [], invrot=tuple(R.T.T.ravel()), tanfov=(th * cam.w / cam.h, th), sun=tuple(sunv), alt_m=alt_m,
                          exposure=exposure, style=style, curv_drop=0.0)
        c.enable(moderngl.DEPTH_TEST)
        p = self.prog
        R_px = self.curv_R(cam.eye[2]) if curvature else 0.0
        dist_far = max(cam.eye[1] * 60, 300)
        mvp = cam.mvp_rel(near=max(cam.eye[1] * 0.02, 0.02), far=dist_far * 4)
        p["mvp"].write(mvp.T.copy().tobytes())
        vals = dict(rect=tuple(rect), gamma=tuple(gamma), focus=tuple(focus), dem_size=(self.geo.W, self.geo.H),
                    origin=(self.geo.ox, self.geo.oy), world_n=float(self.n), eye=tuple(cam.eye), exag=exag, curv_R=R_px,
                    sun=tuple(sunv), style=style, china_lift=china_lift, contour_a=contour_a, grat_a=grat_a, haze=haze,
                    alt_m=alt_m, shadow_steps=float(shadow_steps), exposure=exposure, tint_map=tuple(tint_map), map_relief=map_relief)
        for k, v in vals.items():
            if k in p:
                p[k].value = v
        for i, (name, t) in enumerate((("hm", self.t_h), ("alb", self.t_a), ("chn", self.t_c), ("lnd", self.t_l), ("rel", self.t_r), ("slp", self.t_s))):
            t.use(i)
            if name in p:
                p[name].value = i
        self.vao.render()
        c.disable(moderngl.DEPTH_TEST)
