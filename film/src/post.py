"""Post chain: soft-knee bloom pyramid + halation, radial chromatic aberration, filmic tonemap, vignette,
UI composite (premultiplied sRGB), film grain, dithering."""
import numpy as np
import moderngl
from glcore import ctx, Pass, target
from config import W, H

DOWN = """
#version 430
in vec2 uv; uniform sampler2D src; uniform vec2 texel; uniform float thresh; uniform float first; out vec4 f;
vec3 knee(vec3 c){ float br=max(c.r,max(c.g,c.b)); float soft=clamp(br-thresh+0.5,0.0,1.0); soft=soft*soft*0.5; float w=max(soft,br-thresh)/max(br,1e-4); return c*w; }
void main(){
  vec3 a=texture(src,uv+texel*vec2(-1,-1)).rgb, b=texture(src,uv+texel*vec2(1,-1)).rgb,
       c=texture(src,uv+texel*vec2(-1,1)).rgb, d=texture(src,uv+texel*vec2(1,1)).rgb, e=texture(src,uv).rgb;
  vec3 s=(a+b+c+d)*0.125+e*0.5;
  if(first>0.5) s=knee(s);
  f=vec4(s,1.0);
}"""
UP = """
#version 430
in vec2 uv; uniform sampler2D src; uniform sampler2D base; uniform vec2 texel; uniform float w; out vec4 f;
void main(){
  vec3 s=vec3(0);
  s+=texture(src,uv+texel*vec2(-1,-1)).rgb; s+=texture(src,uv+texel*vec2(0,-1)).rgb*2.0; s+=texture(src,uv+texel*vec2(1,-1)).rgb;
  s+=texture(src,uv+texel*vec2(-1,0)).rgb*2.0; s+=texture(src,uv).rgb*4.0; s+=texture(src,uv+texel*vec2(1,0)).rgb*2.0;
  s+=texture(src,uv+texel*vec2(-1,1)).rgb; s+=texture(src,uv+texel*vec2(0,1)).rgb*2.0; s+=texture(src,uv+texel*vec2(1,1)).rgb;
  f=vec4(texture(base,uv).rgb + s/16.0*w,1.0);
}"""
FINAL = """
#version 430
in vec2 uv; out vec4 f;
uniform sampler2D scene; uniform sampler2D bloom; uniform sampler2D ui; uniform sampler2D uiglow;
uniform float bloom_k; uniform float hal_k; uniform float ca; uniform float vig; uniform float grain; uniform float t;
uniform float exposure; uniform float fade; uniform float ui_glow_k; uniform vec2 res; uniform float lift; uniform float shake_ca;
float hash(vec3 p){ p=fract(p*vec3(443.897,441.423,437.195)); p+=dot(p,p.yzx+19.19); return fract((p.x+p.y)*p.z); }
vec3 filmic(vec3 x){ // linear toe, exponential shoulder above 0.62 (predictable darks)
  x*=exposure; vec3 k=vec3(0.62); return mix(x, k+(1.0-k)*(1.0-exp(-(x-k)/(1.0-k))), step(k,x)); }
void main(){
  vec2 c=uv-0.5; float r2=dot(c*vec2(res.x/res.y,1.0),c*vec2(res.x/res.y,1.0));
  float k=(ca+shake_ca)*r2;
  vec3 col;
  col.r=texture(scene,uv-c*k*1.0).r; col.g=texture(scene,uv).g; col.b=texture(scene,uv+c*k*1.0).b;
  vec3 bl; bl.r=texture(bloom,uv-c*k*2.0).r; bl.g=texture(bloom,uv).g; bl.b=texture(bloom,uv+c*k*2.0).b;
  col += bl*bloom_k;
  col += bl*vec3(1.0,0.35,0.15)*hal_k;
  vec3 m=filmic(col);
  m = pow(m, vec3(1.0/2.2));
  m = m*(1.0-lift)+lift*vec3(0.035,0.04,0.05);
  float v=smoothstep(1.25,0.15,length(c*vec2(1.0,0.82))*1.6); m*=mix(1.0,v,vig);
  vec4 u=texture(ui,uv);
  vec3 ug=texture(uiglow,uv).rgb;
  m = m*(1.0-u.a)+u.rgb;
  m += ug*ui_glow_k;
  float n=hash(vec3(floor(uv*res/1.25),floor(t*30.0)))-0.5;
  float n2=hash(vec3(floor(uv*res/2.5)+7.0,floor(t*30.0)+3.0))-0.5;
  float lum=dot(m,vec3(0.299,0.587,0.114));
  m += (n*0.7+n2*0.5)*grain*(0.35+0.65*(1.0-abs(lum*2.0-1.0)));
  m *= fade;
  m += (hash(vec3(uv*res,t))-0.5)/255.0;
  f=vec4(clamp(m,0.0,1.0),1.0);
}"""
BLUR = """
#version 430
in vec2 uv; uniform sampler2D src; uniform vec2 dir; out vec4 f;
void main(){ vec4 a=texture(src,uv)*0.2270; float o[4]=float[](1.3846,3.2308,5.0769,6.9231); float w[4]=float[](0.3162,0.0703,0.0090,0.0004);
 for(int i=0;i<2;i++){ a+=texture(src,uv+dir*o[i])*w[i]; a+=texture(src,uv-dir*o[i])*w[i]; } f=a; }"""

class Post:
    def __init__(self, w=W, h=H, levels=6):
        self.w, self.h = w, h
        self.down = Pass(DOWN); self.up = Pass(UP); self.final = Pass(FINAL); self.blur = Pass(BLUR)
        self.levels = []
        lw, lh = w, h
        for i in range(levels):
            lw, lh = max(lw // 2, 1), max(lh // 2, 1)
            self.levels.append((target(lw, lh), target(lw, lh)))
        self.out_fbo, self.out_tex = target(w, h, comps=4, dtype="f1")
        c = ctx()
        self.t_ui = c.texture((w, h), 4, dtype="f1"); self.t_ui.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.g1 = target(w // 4, h // 4); self.g2 = target(w // 4, h // 4)
        self.ui_dirty = True

    def set_ui(self, rgba_premul_u8):
        self.t_ui.write(np.ascontiguousarray(rgba_premul_u8[::-1]).tobytes())

    def run(self, scene_tex, t, bloom_k=0.06, hal_k=0.015, ca=0.006, vig=0.55, grain=0.035, exposure=1.0, thresh=0.9,
            fade=1.0, ui_glow_k=0.35, lift=0.0, shake_ca=0.0):
        src = scene_tex
        for i, ((fb, tex), _) in enumerate(self.levels):
            self.down.run(fb, [("src", src)], texel=(1.0 / src.width, 1.0 / src.height), thresh=thresh, first=1.0 if i == 0 else 0.0)
            src = tex
        # upsample accumulate: level[i] += up(level[i+1])
        acc = self.levels[-1][0][1]
        for i in range(len(self.levels) - 2, -1, -1):
            (fb, tex), (fb2, tex2) = self.levels[i]
            self.up.run(fb2, [("src", acc), ("base", tex)], texel=(1.0 / acc.width, 1.0 / acc.height), w=1.0)
            acc = tex2
        # ui glow: downsample ui to quarter and blur
        g1f, g1t = self.g1; g2f, g2t = self.g2
        self.blur.run(g1f, [("src", self.t_ui)], dir=(4.0 / self.w, 0))
        self.blur.run(g2f, [("src", g1t)], dir=(0, 4.0 / self.h))
        self.blur.run(g1f, [("src", g2t)], dir=(8.0 / self.w, 0))
        self.blur.run(g2f, [("src", g1t)], dir=(0, 8.0 / self.h))
        self.final.run(self.out_fbo, [("scene", scene_tex), ("bloom", acc), ("ui", self.t_ui), ("uiglow", g2t)],
                       bloom_k=bloom_k, hal_k=hal_k, ca=ca, vig=vig, grain=grain, t=t, exposure=exposure, fade=fade,
                       ui_glow_k=ui_glow_k, res=(float(self.w), float(self.h)), lift=lift, shake_ca=shake_ca)
        return self.out_fbo

    def read(self):
        return np.frombuffer(self.out_fbo.read(components=3, dtype="f1"), np.uint8).reshape(self.h, self.w, 3)[::-1]
