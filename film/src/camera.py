"""Camera with camera-relative matrices (double precision on CPU) + numpy projection for 2D overlays."""
import numpy as np
from config import W, H

def perspective(fov_deg, aspect, near, far):
    t = 1.0 / np.tan(np.radians(fov_deg) / 2)
    m = np.zeros((4, 4))
    m[0, 0] = t / aspect; m[1, 1] = t
    m[2, 2] = (far + near) / (near - far); m[2, 3] = 2 * far * near / (near - far); m[3, 2] = -1
    return m

def look_rot(fwd, up=(0, 1, 0), roll=0.0):
    f = np.asarray(fwd, float); f = f / np.linalg.norm(f)
    u = np.asarray(up, float)
    if abs(np.dot(f, u / np.linalg.norm(u))) > 0.999:
        u = np.array([0, 0, -1.0])
    s = np.cross(f, u); s /= np.linalg.norm(s); u2 = np.cross(s, f)
    if roll:
        c, sn = np.cos(roll), np.sin(roll)
        s, u2 = s * c + u2 * sn, -s * sn + u2 * c
    R = np.eye(4); R[0, :3] = s; R[1, :3] = u2; R[2, :3] = -f
    return R

class Camera:
    def __init__(self, eye, target, fov=35.0, up=(0, 1, 0), roll=0.0, near=0.05, far=6000.0, w=W, h=H):
        self.eye = np.asarray(eye, float); self.target = np.asarray(target, float)
        self.fov, self.up, self.roll, self.near, self.far = fov, up, roll, near, far
        self.w, self.h = w, h
        self.R = look_rot(self.target - self.eye, up, roll)
        self.P = perspective(fov, w / h, near, far)

    def view_rel(self):
        """View matrix for camera-relative positions (world - eye)."""
        return self.R

    def mvp_rel(self, near=None, far=None):
        P = self.P if near is None else perspective(self.fov, self.w / self.h, near, far)
        return (P @ self.R).astype("f4")

    def project(self, pts):
        """pts Nx3 world -> Nx3 (screen x px, screen y px (top=0), depth w). w<=0 means behind."""
        p = np.asarray(pts, float) - self.eye
        hp = np.c_[p, np.ones(len(p))] @ (self.P @ self.R).T
        w = hp[:, 3]
        ws = np.where(np.abs(w) < 1e-9, 1e-9, w)
        x = (hp[:, 0] / ws * 0.5 + 0.5) * self.w
        y = (1 - (hp[:, 1] / ws * 0.5 + 0.5)) * self.h
        return np.c_[x, y, w]
