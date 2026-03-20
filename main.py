import cv2 as cv
import numpy as np
from gen_mesh import gen_mesh


def process_image2(file_path: str):
    img = cv.imread(file_path, cv.IMREAD_GRAYSCALE)
    mask = cv.inRange(img, 0, 50)
    mask = cv.dilate(mask, kernel=np.ones((3, 3), np.uint8), iterations=2)
    n, labels, stats, _ = cv.connectedComponentsWithStats(mask, connectivity=8)
    largest = 1 + np.argmax(stats[1:, cv.CC_STAT_AREA])
    mask = labels == largest
    return mask


def process_image1(file_path: str):
    img = cv.imread(file_path, cv.IMREAD_GRAYSCALE)
    mask = cv.inRange(img, 0, 50)
    n, labels, stats, _ = cv.connectedComponentsWithStats(mask, connectivity=8)
    largest = 1 + np.argmax(stats[1:, cv.CC_STAT_AREA])
    mask = labels == largest
    return mask


if __name__ == "__main__":
    import trimesh

    # file_path = "example/chun/image2.jpeg"
    # mask = process_image2(file_path)
    file_path = "example/chun/image1.png"
    mask = process_image1(file_path)
    vertices, faces = gen_mesh(mask, 200, 5.0)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    mesh.export("example/chun/chun.stl")
    shit = 0
