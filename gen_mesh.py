from shapely.geometry import Polygon
import numpy as np
import triangle as tr
import cv2 as cv


def extract_contour(mask: np.ndarray):
    mask = cv.flip(mask.astype(np.uint8), 0)
    contours, hierarchy = cv.findContours(
        mask.astype(np.uint8), cv.RETR_CCOMP, cv.CHAIN_APPROX_SIMPLE
    )
    if hierarchy is None:
        return [], []

    hierarchy = hierarchy[0]  # shape (N, 4): [next, prev, first_child, parent]
    outer_list = []
    inner_list = []

    for i, (contour, (next_, prev, child, parent)) in enumerate(
        zip(contours, hierarchy)
    ):
        pts = contour[:, 0, :][
            ::-1
        ]  # findContours returns CCW outer boundary when viewed from image front (Y-down); viewed from 3D top (Y-up), this becomes CW, so reverse
        if parent == -1:
            outer_list.append(pts)
        else:
            inner_list.append(pts)
    outer_list = [
        cv.approxPolyDP(outer, epsilon=1.0, closed=True).reshape(-1, 2)
        for outer in outer_list
    ]
    inner_list = [
        cv.approxPolyDP(inner, epsilon=1.0, closed=True).reshape(-1, 2)
        for inner in inner_list
    ]
    return outer_list, inner_list


def build_mesh(outers: list, inners: list, height=10.0):
    offset = 0
    hole_points = [[10000, 10000]]
    for inner in inners:
        hole_point = Polygon(inner[:, :2]).representative_point()
        hole_points.append([hole_point.x, hole_point.y])
    bottom_lut = []
    top_lut = []
    all_pts = []
    all_faces = []
    faces = []
    offset = 0
    local_offset = 0
    segs = []
    for poly in outers + inners:
        bottom = np.hstack([poly[:, :2], np.zeros((len(poly), 1))])
        bottom_indices = np.arange(offset, offset + len(bottom))
        bottom_lut.append(bottom_indices)
        all_pts.append(bottom)
        offset += len(bottom)

        top = np.hstack([poly[:, :2], np.full((len(poly), 1), height)])
        all_pts.append(top)
        top_indices = np.arange(offset, offset + len(top))
        top_lut.append(top_indices)
        offset += len(top)

        # build side faces
        faces = np.zeros((2 * len(bottom), 3), dtype=np.int32)
        faces[0::2, 0] = bottom_indices
        faces[0::2, 1] = np.roll(bottom_indices, -1)
        faces[0::2, 2] = top_indices
        faces[1::2, 0] = top_indices
        faces[1::2, 1] = np.roll(bottom_indices, -1)
        faces[1::2, 2] = np.roll(top_indices, -1)
        all_faces.append(faces)

        # prepare for building top/bottom faces
        local_indices = np.arange(local_offset, local_offset + len(bottom))
        local_offset += len(bottom)
        segs.append(
            np.hstack(
                [
                    local_indices.reshape(-1, 1),
                    np.roll(local_indices, -1).reshape(-1, 1),
                ]
            )
        )

    all_pts = np.vstack(all_pts)
    bottom_lut = np.hstack(bottom_lut)
    top_lut = np.hstack(top_lut)
    segs = np.vstack(segs)
    pts_2d = all_pts[bottom_lut][:, :2]
    a = dict(vertices=pts_2d, segments=segs, holes=hole_points)
    b = tr.triangulate(a, "p")
    local_faces = b["triangles"]
    top_faces = top_lut[local_faces]
    bottom_faces = bottom_lut[local_faces][:, [2, 1, 0]]
    all_faces = np.vstack(all_faces + [top_faces, bottom_faces])
    return all_pts, all_faces


def gen_mesh(mask, dst_size, dst_height):
    outer_list, inner_list = extract_contour(mask)

    # compute max long side of minimum bounding rectangle across all outer polys
    max_long_side = 0.0
    for poly in outer_list:
        pts = poly.astype(np.float32).reshape(-1, 1, 2)
        _, (w, h), _ = cv.minAreaRect(pts)
        max_long_side = max(max_long_side, w, h)

    scale = dst_size / max_long_side if max_long_side > 0 else 1.0
    outer_list = [(poly * scale).astype(np.float32) for poly in outer_list]
    inner_list = [(poly * scale).astype(np.float32) for poly in inner_list]

    return build_mesh(outer_list, inner_list, height=dst_height)
