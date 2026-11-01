from decimal import Decimal
from typing import List, Tuple


def get_orthogonal_rotations(
    length: Decimal,
    width: Decimal,
    height: Decimal,
    allow_upright_only: bool = False,
) -> List[Tuple[Decimal, Decimal, Decimal]]:
    """
    Generates unique 3D orthogonal orientations (dx, dy, dz) for a cuboid.
    
    If allow_upright_only is False (default):
        Returns up to 6 unique orthogonal rotations.
    If allow_upright_only is True:
        Returns up to 2 unique rotations keeping the height axis strictly vertical.
    
    Duplicate orientations (e.g. for cubes or square prisms) are removed
    to eliminate redundant collision checks and maximize packing performance.
    """
    if allow_upright_only:
        candidates = [
            (length, width, height),
            (width, length, height),
        ]
    else:
        candidates = [
            (length, width, height),
            (length, height, width),
            (width, length, height),
            (width, height, length),
            (height, length, width),
            (height, width, length),
        ]

    # Deduplicate while preserving deterministic order
    unique_rotations: List[Tuple[Decimal, Decimal, Decimal]] = []
    seen = set()
    for rot in candidates:
        if rot not in seen:
            seen.add(rot)
            unique_rotations.append(rot)

    return unique_rotations

