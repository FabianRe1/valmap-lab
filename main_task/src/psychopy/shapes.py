"""
Geometry for the practice shapes.

Practice explains the task's logic without teaching any video material, so it is drawn rather than
played: one COLOR per journey, one SHAPE per step. This module owns the vertex maths only; the two
arms draw the same figures from it (PsychoPy as ShapeStim vertices, jsPsych as SVG polygons), so a
participant sees the same practice in the lab and in the browser.

Vertices are unit coordinates centred on the origin, spanning -0.5 to 0.5, listed counter-clockwise.
Mirrored by ../jspsych/shapes.js; tests/check_parity.py compares the two vertex for vertex.
"""

import math

import config as cfg

SHAPE_ID_PREFIX = "shp"


def is_shape_id(stim_id):
    """True for a practice shape id (`shp01`..`shpNN`), false for a real clip id (`Aimg1`..)."""
    return bool(stim_id) and stim_id.startswith(SHAPE_ID_PREFIX)


def shape_index(stim_id):
    """`shpNN` -> (journey, step), both 0-based.

    The ids run journey-major over cfg.N_STEPS steps, exactly as practice.rebuild() slices them,
    so the divisor is the route length and NOT a literal 4: at 3 steps shp04 is journey 1 step 0,
    at 4 steps it is journey 0 step 3. Getting this wrong makes a practice journey change colour
    part way through, which is the very thing practice uses to signal a structure change.
    """
    n = int(stim_id[len(SHAPE_ID_PREFIX):]) - 1
    return n // cfg.N_STEPS, n % cfg.N_STEPS


def shape_name(stim_id):
    return cfg.PRACTICE_SHAPE_STEPS[shape_index(stim_id)[1]]


def shape_color(stim_id):
    return cfg.PRACTICE_SHAPE_COLORS[shape_index(stim_id)[0]]


def _regular_polygon(n_sides, rotation_deg):
    """n evenly spaced vertices on a circle of radius 0.5, first vertex at `rotation_deg`."""
    rot = math.radians(rotation_deg)
    return [(0.5 * math.cos(rot + 2 * math.pi * i / n_sides),
             0.5 * math.sin(rot + 2 * math.pi * i / n_sides))
            for i in range(n_sides)]


def _star(points=5, inner_ratio=0.4):
    """A `points`-pointed star: outer radius 0.5, inner radius 0.5 * inner_ratio, apex upwards."""
    verts = []
    for i in range(points * 2):
        radius = 0.5 if i % 2 == 0 else 0.5 * inner_ratio
        angle = math.pi / 2 + i * math.pi / points
        verts.append((radius * math.cos(angle), radius * math.sin(angle)))
    return verts


def vertices(name):
    """Unit vertices for one shape name, counter-clockwise, spanning -0.5 to 0.5."""
    if name == "square":
        return [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]
    if name == "triangle":
        return _regular_polygon(3, 90)
    if name == "circle":
        return _regular_polygon(64, 0)
    if name == "star":
        return _star()
    raise KeyError(f"unknown practice shape '{name}'; have {list(cfg.PRACTICE_SHAPE_STEPS)}")


def vertices_for(stim_id):
    return vertices(shape_name(stim_id))
