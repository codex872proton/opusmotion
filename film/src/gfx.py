"""GL layers: stylised relief map, 3D D-21 mesh, compositing + blur passes."""
import numpy as np
import moderngl
from glcore import ctx, Pass, target, upload
from terrain import Terrain, VS as TERRAIN_VS
from config import W, H

MAP_FS = """
#version 430
in vec2 uv; in vec3 wpos; in float hm_m; in float lat;
uniform sampler2D hm; uniform sampler2D alb; uniform sampler2D chn; uniform sampler2D lnd; uniform sampler2D rel; uniform sampler2D slp;
uniform vec2 dem_size; uniform vec2 origin; uniform float world_n;
uniform vec3 sun; uniform float exag;
uniform float china_lift, contour_a, grat_a, detail, dimmer, land_lift;
uniform vec4 spot;      // local px x,y, radius px, gain
uniform vec4 spot2;
uniform float fog_k; uniform vec3 fog_c;
out vec4 frag;
vec3 L(vec3 srgb){ return pow(srgb, vec3(2.2)); }
void main(){
  vec2 tc = vec2(uv.x, 1.0-uv.y);
  vec2 px = uv*dem_size;
  float s = max(max(fwidth(px).x, fwidth(px).y), 1.0);
  float lod = log2(s);
  vec2 sl = texture(slp, tc).rg;
  vec3 n = normalize(vec3(-sl.x*exag*0.6, 1.0, -sl.y*exag*0.6));
  float lam = clamp(dot(n, sun), 0.0, 1.0);
  float rel_ = texture(rel, tc).r;
  float shade = clamp(0.50*rel_ + 0.80*lam - 0.22, 0.0, 1.0);
  float land = smoothstep(0.3, 0.7, texture(lnd, tc).r);
  float china = texture(chn, tc).r;
  float hs = textureLod(hm, tc, lod+0.5).r;
  vec3 a = texture(alb, tc).rgb;
  float alum = dot(a, vec3(0.3,0.55,0.15));
  // ocean with faint bathymetry
  vec3 ocean = mix(L(vec3(0.020,0.031,0.046)), L(vec3(0.040,0.066,0.090)), smoothstep(-5000.0,-60.0,hs));
  // land
  vec3 g0 = L(vec3(0.045,0.056,0.070)), g1 = L(vec3(0.200,0.222,0.250));
  vec3 ground = mix(g0, g1, pow(shade,1.25)) * (1.0+land_lift);
  vec3 c0 = L(vec3(0.070,0.066,0.062)), c1 = L(vec3(0.560,0.488,0.398));
  vec3 cn = mix(c0, c1, pow(shade,1.45));
  cn *= mix(1.0, 0.55 + 0.95*alum, detail);           // real surface texture (dunes, salt flats)
  ground = mix(ground, cn, china*china_lift);
  vec3 mapc = mix(ocean, ground, land);
  // coastline sheen
  mapc += L(vec3(0.33,0.40,0.47))*0.12*(1.0-abs(land*2.0-1.0));
  // contours (500 m, index 2500 m)
  float hc2 = textureLod(hm, tc, max(lod+0.6,0.0)).r;
  float cv = hc2/500.0; float cw = fwidth(cv);
  float cl = 1.0 - smoothstep(0.0, cw*1.2, abs(fract(cv-0.5)-0.5));
  float iv = hc2/2500.0; float iw = fwidth(iv);
  float il = 1.0 - smoothstep(0.0, iw*1.5, abs(fract(iv-0.5)-0.5));
  float cfade = clamp(1.6 - cw*5.0, 0.0, 1.0);
  mapc += L(vec3(0.72,0.70,0.66))*(cl*0.05 + il*0.10)*contour_a*cfade*step(300.0,hc2)*land;
  // graticule 5 deg
  float lon = (px.x+origin.x)/world_n*360.0-180.0;
  float latd = degrees(lat);
  vec2 gq = vec2(lon, latd)/5.0; vec2 gwd = fwidth(gq);
  vec2 gl = 1.0 - smoothstep(vec2(0.0), gwd*1.1, abs(fract(gq-0.5)-0.5));
  mapc += L(vec3(0.45,0.55,0.65))*max(gl.x,gl.y)*0.10*grat_a;
  float dist = length(wpos);
  mapc = mix(mapc, L(fog_c), 1.0-exp(-dist*fog_k));
  // local spotlights
  float d1 = length(px - spot.xy)/max(spot.z,1.0);
  float d2 = length(px - spot2.xy)/max(spot2.z,1.0);
  mapc *= 1.0 + spot.w*exp(-d1*d1) + spot2.w*exp(-d2*d2);
  frag = vec4(mapc*dimmer, 1.0);
}
"""

class MapGL(Terrain):
    def __init__(self, geo, grid=(820, 820)):
        super().__init__(geo, grid)
        c = ctx()
        gx, gy = grid
        xs = np.linspace(0, 1, gx, dtype="f4"); ys = np.linspace(0, 1, gy, dtype="f4")
        X, Y = np.meshgrid(xs, ys)
        v = np.stack([X, Y], -1).reshape(-1, 2)
        I = (np.arange(gy - 1)[:, None] * gx + np.arange(gx - 1)[None, :]).ravel()
        tri = np.stack([I, I + gx, I + 1, I + 1, I + gx, I + gx + 1], -1).ravel().astype("i4")
        self.mprog = c.program(vertex_shader=TERRAIN_VS, fragment_shader=MAP_FS)
        self.mvao = c.vertex_array(self.mprog, [(c.buffer(v.tobytes()), "2f", "g")], c.buffer(tri.tobytes()))

    def render_map(self, fbo, cam, rect, sun=(-0.45, 0.6, -0.65), exag=4.0, curvature=True, china_lift=1.0, contour_a=1.0,
                   grat_a=1.0, detail=0.5, dimmer=1.0, land_lift=0.0, spot=(0, 0, 1, 0), spot2=(0, 0, 1, 0), clear=True, fog_k=0.0, fog_c=(0.03, 0.045, 0.06)):
        from geo import m_per_px
        c = ctx()
        fbo.use()
        if clear:
            fbo.clear(0.0016, 0.0026, 0.004, 1.0, depth=1.0)
        c.enable(moderngl.DEPTH_TEST)
        p = self.mprog
        sunv = np.asarray(sun, float); sunv /= np.linalg.norm(sunv)
        R_px = self.curv_R(cam.eye[2]) if curvature else 0.0
        dist_far = max(cam.eye[1] * 60, 300)
        mvp = cam.mvp_rel(near=max(cam.eye[1] * 0.02, 0.02), far=dist_far * 4)
        p["mvp"].write(mvp.T.copy().tobytes())
        vals = dict(rect=tuple(rect), gamma=(1.0, 1.0), focus=(0.5, 0.5), dem_size=(self.geo.W, self.geo.H),
                    origin=(self.geo.ox, self.geo.oy), world_n=float(self.n), eye=tuple(cam.eye), exag=exag, curv_R=R_px,
                    sun=tuple(sunv), china_lift=china_lift, contour_a=contour_a, grat_a=grat_a, detail=detail, dimmer=dimmer,
                    land_lift=land_lift, spot=tuple(spot), spot2=tuple(spot2), fog_k=fog_k, fog_c=tuple(fog_c))
        for k, v in vals.items():
            if k in p:
                p[k].value = v
        for i, (name, t) in enumerate((("hm", self.t_h), ("alb", self.t_a), ("chn", self.t_c), ("lnd", self.t_l), ("rel", self.t_r), ("slp", self.t_s))):
            t.use(i)
            if name in p:
                p[name].value = i
        self.mvao.render()
        c.disable(moderngl.DEPTH_TEST)

    def project(self, cam, lon, lat, exag=4.0, alt_m=None, curvature=True):
        """lon/lat arrays -> screen Nx3 (x, y, w)."""
        pts = self.world(np.atleast_1d(lon), np.atleast_1d(lat), alt_m=alt_m, exag=exag)
        pts = self.curve(pts, cam, curvature)
        return cam.project(pts)

# ------------------------------------------------------------------ D-21 geometry (shared with 2D drawings)
def d21_halfspan(x):
    """Planform half-width (fraction of length) at station x (0 nose .. 1 tail)."""
    x = np.asarray(x, float)
    r = d21_radius(x)
    # ogee leading edge: cubic bezier (0.03,r0) -> (0.87,0.222)
    P = np.array([[0.035, 0.036], [0.33, 0.064], [0.65, 0.175], [0.875, 0.222]])
    tt = np.linspace(0, 1, 400)
    B = ((1 - tt) ** 3)[:, None] * P[0] + (3 * (1 - tt) ** 2 * tt)[:, None] * P[1] + (3 * (1 - tt) * tt ** 2)[:, None] * P[2] + (tt ** 3)[:, None] * P[3]
    le = np.interp(x, B[:, 0], B[:, 1], left=0.0, right=0.222)
    w = np.where((x >= 0.035) & (x <= 0.905), np.where(x > 0.875, 0.222, le), 0.0)
    return np.maximum(w, r)

def d21_radius(x):
    x = np.asarray(x, float)
    r = np.where(x < 0.0, 0.0, 0.0331 + 0.004 * np.clip(x / 0.04, 0, 1))
    r = np.where(x > 0.9, 0.0371 - (x - 0.9) / 0.1 * 0.006, r)
    return np.where(x > 1.0, 0.0, r)

def _smax(a, b, k):
    h = np.clip(0.5 + 0.5 * (a - b) / k, 0, 1)
    return a * h + b * (1 - h) + k * h * (1 - h)

def build_d21_mesh(nx=200, ny=90):
    """Returns (positions Nx3, normals Nx3, part N, triangle indices). Model frame: x nose->tail, y up, z span."""
    xs = np.concatenate([np.linspace(0.0, 0.05, 20), np.linspace(0.05, 0.86, nx - 60)[1:], np.linspace(0.86, 0.91, 25)[1:],
                         np.linspace(0.91, 1.0, 16)[1:]])
    us = np.sin(np.linspace(-np.pi / 2, np.pi / 2, ny))      # denser at edges
    verts, parts = [], []
    def surf(sign):
        V = np.zeros((len(xs), ny, 3))
        for i, x in enumerate(xs):
            r = float(d21_radius(x)); w = float(d21_halfspan(x))
            y = us * w
            body = np.sqrt(np.clip(r * r - y * y, 0, None))
            th = 0.0105 * np.clip(1 - (np.abs(y) / max(w, 1e-6)) ** 2, 0, 1) ** 0.6 * np.clip((x - 0.03) / 0.3, 0.15, 1.0)
            z = _smax(body * (1.0 if sign > 0 else 0.86), th * (1.0 if sign > 0 else 0.7), 0.012)
            V[i, :, 0] = x; V[i, :, 1] = sign * z; V[i, :, 2] = y
        return V
    top, bot = surf(1), surf(-1)
    def grid_tris(V, flip):
        nI, nJ = V.shape[:2]
        base = len(verts)
        verts.extend(V.reshape(-1, 3)); parts.extend([0.0] * (nI * nJ))
        I = (np.arange(nI - 1)[:, None] * nJ + np.arange(nJ - 1)[None, :]).ravel() + base
        t = np.stack([I, I + nJ, I + 1, I + 1, I + nJ, I + nJ + 1], -1) if not flip else np.stack([I, I + 1, I + nJ, I + 1, I + nJ + 1, I + nJ], -1)
        return t.reshape(-1)
    tris = [grid_tris(top, False), grid_tris(bot, True)]
    # inlet spike (cone) and dark inlet face, nozzle face
    def disc(x, r_in, r_out, part, facing, n=48, cone_tip=None):
        base = len(verts)
        ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
        for a in ang:
            verts.append((x, r_out * np.sin(a), r_out * np.cos(a))); parts.append(part)
        if cone_tip is None:
            verts.append((x, 0, 0)); parts.append(part)
        else:
            verts.append(cone_tip); parts.append(part)
        c = base + n
        t = []
        for k in range(n):
            a0, a1 = base + k, base + (k + 1) % n
            t.extend((a0, a1, c) if facing > 0 else (a1, a0, c))
        return np.array(t)
    tris.append(disc(0.0, 0, 0.0331, 1.0, -1))
    tris.append(disc(0.0, 0, 0.019, 3.0, -1, cone_tip=(-0.05, 0, 0)))
    tris.append(disc(1.0, 0, 0.0311, 2.0, 1))
    # vertical fin (thin slab)
    fin = [(0.67, 0.034), (0.865, 0.128), (0.965, 0.128), (0.952, 0.034)]
    tfin = 0.0028
    base = len(verts)
    for sgn in (1, -1):
        for (x, y) in fin:
            verts.append((x, y, sgn * tfin)); parts.append(0.0)
    f = []
    f += [base + 0, base + 1, base + 2, base + 0, base + 2, base + 3]
    f += [base + 4, base + 6, base + 5, base + 4, base + 7, base + 6]
    for k in range(4):
        a, b = base + k, base + (k + 1) % 4
        f += [a, b + 4, b, a, a + 4, b + 4]
    tris.append(np.array(f))
    P = np.array(verts, "f4"); T = np.concatenate(tris).astype("i4"); parts = np.array(parts, "f4")
    # normals
    N = np.zeros_like(P)
    tri = T.reshape(-1, 3)
    fn = np.cross(P[tri[:, 1]] - P[tri[:, 0]], P[tri[:, 2]] - P[tri[:, 0]])
    for k in range(3):
        np.add.at(N, tri[:, k], fn)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    return P, N.astype("f4"), parts, T

DRONE_VS = """
#version 430
in vec3 pos; in vec3 nrm; in float part;
uniform mat4 mvp; uniform mat4 model;
out vec3 wn; out vec3 wp; out float pt; out vec3 mp;
void main(){
  vec4 w = model*vec4(pos,1.0);
  wp = w.xyz; mp = pos;
  wn = normalize(mat3(model)*nrm);
  pt = part;
  gl_Position = mvp*w;
}
"""
DRONE_FS = """
#version 430
in vec3 wn; in vec3 wp; in float pt; in vec3 mp;
uniform vec3 sun; uniform float glow; uniform float alpha; uniform vec3 rimc; uniform float hatch_hi; uniform float clip_y; uniform float light_k; uniform float res_y;
out vec4 f;
void main(){
  float sy = res_y - gl_FragCoord.y;
  if (clip_y > -0.5 && sy > clip_y) discard;
  vec3 n = normalize(wn);
  vec3 v = normalize(-wp);
  if (dot(n,v) < 0.0) n = -n;
  vec3 base = vec3(0.0075,0.0082,0.0098);
  if (pt > 0.5 && pt < 1.5) base = vec3(0.002);
  if (pt > 2.5) base = vec3(0.06,0.062,0.068);
  float ndl = max(dot(n, sun), 0.0);
  vec3 h = normalize(sun + v);
  float fres = 0.04 + 0.96*pow(1.0-max(dot(n,v),0.0), 5.0);
  float spec = pow(max(dot(n,h),0.0), 140.0)*3.0 + pow(max(dot(n,h),0.0), 18.0)*0.10;
  vec3 r = reflect(-v, n);
  vec3 env = mix(vec3(0.010,0.012,0.016), vec3(0.18,0.23,0.30), smoothstep(-0.2,0.8,r.y));
  vec3 c = base*(ndl*2.4 + 0.15) + vec3(1.0,0.92,0.80)*spec*(0.18+fres) + env*fres*0.55;
  c += rimc*pow(1.0-max(dot(n,v),0.0), 3.5)*0.5;
  // panel seams: faint lines along stations
  float seam = 1.0 - smoothstep(0.0, 0.0012, abs(fract(mp.x*9.0)-0.5)*0.11);
  c *= 1.0 - 0.25*seam*step(0.03, abs(mp.z));
  if (pt > 1.5 && pt < 2.5) c = vec3(1.0,0.42,0.12)*glow*3.0 + vec3(0.02);
  // hatch highlight (underside forward bay)
  float hb = step(mp.y, 0.0)*step(0.075, mp.x)*step(mp.x, 0.30)*step(abs(mp.z), 0.034);
  c = mix(c, vec3(0.95,0.62,0.14)*0.9, hb*hatch_hi);
  c *= light_k;
  if (clip_y > -0.5) c += vec3(0.55,0.75,1.0)*exp(-pow((clip_y-sy)/5.0,2.0))*3.0;
  f = vec4(c*alpha, alpha);
}
"""

def rot_matrix(yaw, pitch, roll):
    """Model frame (x forward-nose->tail axis) -> world. yaw about +y, pitch about z, roll about x."""
    cy, sy = np.cos(yaw), np.sin(yaw); cp, sp = np.cos(pitch), np.sin(pitch); cr, sr = np.cos(roll), np.sin(roll)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cp, -sp, 0], [sp, cp, 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    return Ry @ Rz @ Rx

class Drone3D:
    def __init__(self):
        c = ctx()
        P, N, parts, T = build_d21_mesh()
        data = np.concatenate([P, N, parts[:, None]], 1).astype("f4")
        self.prog = c.program(vertex_shader=DRONE_VS, fragment_shader=DRONE_FS)
        self.vao = c.vertex_array(self.prog, [(c.buffer(data.tobytes()), "3f 3f 1f", "pos", "nrm", "part")], c.buffer(T.tobytes()))
        self.ms_fbo = c.framebuffer(color_attachments=[c.renderbuffer((W, H), 4, samples=4, dtype="f2")],
                                    depth_attachment=c.depth_renderbuffer((W, H), samples=4))
        self.fbo, self.tex = target(W, H, comps=4, dtype="f2")

    def render(self, cam, center, length_px, yaw, pitch=0.0, roll=0.0, sun=(-0.4, 0.8, -0.3), glow=1.0, alpha=1.0,
               rim=(0.55, 0.42, 0.30), hatch_hi=0.0, clip_y=-1.0, light_k=1.0):
        """center: world position (same space as camera). Returns premultiplied linear RGBA texture."""
        c = ctx()
        R = rot_matrix(yaw, pitch, roll) * length_px
        M = np.eye(4)
        M[:3, :3] = R
        # model origin at body mid-length
        M[:3, 3] = np.asarray(center, float) - cam.eye - R @ np.array([0.5, 0, 0])
        self.last = (M, cam)
        dist = np.linalg.norm(np.asarray(center) - cam.eye)
        mvp = cam.mvp_rel(near=max(dist * 0.05, 1e-3), far=dist * 4)
        p = self.prog
        p["mvp"].write(mvp.T.astype("f4").copy().tobytes())
        p["model"].write(M.T.astype("f4").copy().tobytes())
        s = np.asarray(sun, float); s /= np.linalg.norm(s)
        for k, v in dict(sun=tuple(s), glow=glow, alpha=alpha, rimc=tuple(rim), hatch_hi=hatch_hi, clip_y=float(clip_y), light_k=light_k, res_y=float(H)).items():
            if k in p: p[k].value = v
        self.ms_fbo.use()
        self.ms_fbo.clear(0, 0, 0, 0, depth=1.0)
        c.enable(moderngl.DEPTH_TEST)
        self.vao.render()
        c.disable(moderngl.DEPTH_TEST)
        c.copy_framebuffer(self.fbo, self.ms_fbo)
        return self.tex

    def project_model(self, pts):
        """Model-space points (x nose->tail, y up, z span) -> screen px via the last render's transforms."""
        M, cam = self.last
        P = np.c_[np.asarray(pts, float), np.ones(len(pts))] @ M.T
        return cam.project(P[:, :3] + cam.eye)

COMP_FS = """
#version 430
in vec2 uv; out vec4 f;
uniform sampler2D scene; uniform sampler2D ov; uniform sampler2D drone; uniform sampler2D em;
uniform float em_gain; uniform float use_drone; uniform vec3 bg; uniform float scene_k;
vec3 lin(vec4 c){ return c.a > 0.0 ? pow(c.rgb/c.a, vec3(2.2))*c.a : vec3(0.0); }
void main(){
  vec3 s = mix(bg, texture(scene, uv).rgb, scene_k);
  vec4 o = texture(ov, uv);
  s = s*(1.0-o.a) + lin(o);
  if (use_drone > 0.5){ vec4 d = texture(drone, uv); s = s*(1.0-d.a) + d.rgb; }
  vec4 e = texture(em, uv);
  s += lin(e)*em_gain;
  f = vec4(s, 1.0);
}
"""
DIRBLUR_FS = """
#version 430
in vec2 uv; out vec4 f;
uniform sampler2D src; uniform vec2 d; uniform float taps;
void main(){
  vec4 a = vec4(0.0); float wsum = 0.0;
  int n = int(taps);
  for (int i=0;i<n;i++){
    float t = (float(i)/(float(n)-1.0)) - 0.5;
    float w = 1.0 - abs(t)*0.8;
    a += texture(src, uv + d*t)*w; wsum += w;
  }
  f = a/wsum;
}
"""

class Compositor:
    def __init__(self):
        c = ctx()
        self.comp = Pass(COMP_FS)
        self.dblur = Pass(DIRBLUR_FS)
        self.scene_fbo, self.scene_tex = target(depth=True)
        self.tmp_fbo, self.tmp_tex = target()
        self.tmp2_fbo, self.tmp2_tex = target()
        self.out_fbo, self.out_tex = target()
        self.t_ov = c.texture((W, H), 4, dtype="f1"); self.t_em = c.texture((W, H), 4, dtype="f1")
        for t in (self.t_ov, self.t_em):
            t.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.blank = c.texture((W, H), 4, dtype="f1"); self.blank.write(np.zeros((H, W, 4), np.uint8).tobytes())

    def blur(self, tex, dx, dy, taps=14):
        """Directional blur in pixels; returns texture."""
        if abs(dx) < 0.3 and abs(dy) < 0.3:
            return tex
        self.dblur.run(self.tmp_fbo, [("src", tex)], d=(dx / W, dy / H), taps=float(taps))
        return self.tmp_tex

    def defocus(self, tex, r, taps=10):
        if r < 0.4:
            return tex
        self.dblur.run(self.tmp_fbo, [("src", tex)], d=(2 * r / W, 0.0), taps=float(taps))
        self.dblur.run(self.tmp2_fbo, [("src", self.tmp_tex)], d=(0.0, 2 * r / H), taps=float(taps))
        return self.tmp2_tex

    def run(self, scene_tex, ov_arr=None, em_arr=None, drone_tex=None, em_gain=3.0, bg=(0.0016, 0.0024, 0.0036), scene_k=1.0):
        if ov_arr is not None:
            self.t_ov.write(np.ascontiguousarray(ov_arr[::-1]).tobytes())
        if em_arr is not None:
            self.t_em.write(np.ascontiguousarray(em_arr[::-1]).tobytes())
        texs = [("scene", scene_tex if scene_tex is not None else self.blank),
                ("ov", self.t_ov if ov_arr is not None else self.blank),
                ("drone", drone_tex if drone_tex is not None else self.blank),
                ("em", self.t_em if em_arr is not None else self.blank)]
        self.comp.run(self.out_fbo, texs, em_gain=em_gain, use_drone=1.0 if drone_tex is not None else 0.0, bg=tuple(bg),
                      scene_k=scene_k if scene_tex is not None else 0.0)
        return self.out_tex
