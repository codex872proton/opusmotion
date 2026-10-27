"""Render a time range of the film to an H.264 segment: python3 render.py START END OUT [FPS]"""
import sys, subprocess, time
import numpy as np
from config import W, H
import film

def main():
    t0, t1, out = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    fps = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    n0, n1 = int(round(t0 * fps)), int(round(t1 * fps))
    R = film.Renderer()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-tune", "film",
                           "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                           "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    st = time.time()
    for n in range(n0, n1):
        img = R.frame(min(n / fps, film.DUR - 1e-4))
        ff.stdin.write(np.ascontiguousarray(img).tobytes())
        if (n - n0) % 60 == 0:
            print(f"{out}: {n - n0}/{n1 - n0} {time.time() - st:.0f}s", flush=True)
    ff.stdin.close(); ff.wait()
    print(f"done {out} {n1 - n0} frames in {time.time() - st:.0f}s", flush=True)

if __name__ == "__main__":
    main()
