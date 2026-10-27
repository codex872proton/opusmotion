"""ModernGL (EGL headless) core: context, shader cache, render targets, fullscreen passes."""
import numpy as np
import moderngl
from config import W, H

_ctx = None

def ctx():
    global _ctx
    if _ctx is None:
        _ctx = moderngl.create_standalone_context(backend="egl", require=430)
    return _ctx

FS_VERT = """
#version 430
in vec2 in_pos; out vec2 uv;
void main(){ uv = in_pos*0.5+0.5; gl_Position = vec4(in_pos,0.0,1.0); }
"""

_quad = None
_progs = {}

def quad_vbo():
    global _quad
    if _quad is None:
        _quad = ctx().buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4").tobytes())
    return _quad

class Pass:
    """Fullscreen fragment pass."""
    def __init__(self, frag, name=None):
        c = ctx()
        self.prog = c.program(vertex_shader=FS_VERT, fragment_shader=frag)
        self.vao = c.vertex_array(self.prog, [(quad_vbo(), "2f", "in_pos")])

    def set(self, **u):
        for k, v in u.items():
            if k in self.prog:
                m = self.prog[k]
                if isinstance(v, (tuple, list, np.ndarray)):
                    m.value = tuple(np.asarray(v, dtype="f4").ravel().tolist()) if np.asarray(v).size > 1 else float(np.asarray(v).ravel()[0])
                else:
                    m.value = v
        return self

    def run(self, fbo, textures=(), **u):
        for i, (name, tex) in enumerate(textures):
            tex.use(location=i)
            if name in self.prog:
                self.prog[name].value = i
        self.set(**u)
        fbo.use()
        self.vao.render(moderngl.TRIANGLE_STRIP)

def target(w=W, h=H, comps=4, dtype="f2", samples=0, depth=False):
    c = ctx()
    if samples:
        rb = c.renderbuffer((w, h), comps, samples=samples, dtype=dtype)
        db = c.depth_renderbuffer((w, h), samples=samples) if depth else None
        return c.framebuffer(color_attachments=[rb], depth_attachment=db), rb
    tex = c.texture((w, h), comps, dtype=dtype)
    tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    tex.repeat_x = tex.repeat_y = False
    db = c.depth_renderbuffer((w, h)) if depth else None
    return c.framebuffer(color_attachments=[tex], depth_attachment=db), tex

def upload(img, tex=None, dtype="f1"):
    """img: HxWxC numpy (uint8 or float). Flipped so row 0 = top of the image."""
    c = ctx()
    h, w = img.shape[:2]; comps = 1 if img.ndim == 2 else img.shape[2]
    data = np.ascontiguousarray(img[::-1])
    if tex is None or tex.size != (w, h) or tex.components != comps:
        tex = c.texture((w, h), comps, dtype=dtype)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
    tex.write(data.tobytes())
    return tex
