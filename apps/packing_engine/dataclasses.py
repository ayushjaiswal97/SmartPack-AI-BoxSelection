from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional


@dataclass(frozen=True)
class ItemDTO:
    """Represents an individual physical item to be packed."""
    item_id: str
    sku: str
    name: str
    length: Decimal
    width: Decimal
    height: Decimal
    weight: Decimal

    @property
    def volume(self) -> Decimal:
        return self.length * self.width * self.height

    @property
    def sorted_dimensions(self) -> tuple[Decimal, Decimal, Decimal]:
        """Returns (dim1, dim2, dim3) in ascending order for boundary comparison."""
        return tuple(sorted([self.length, self.width, self.height]))  # type: ignore


@dataclass(frozen=True)
class BoxDTO:
    """Represents a candidate shipping box."""
    box_id: int
    name: str
    length: Decimal
    width: Decimal
    height: Decimal
    max_weight: Decimal
    packaging_cost: Decimal
    is_active: bool = True

    @property
    def volume(self) -> Decimal:
        return self.length * self.width * self.height

    @property
    def sorted_dimensions(self) -> tuple[Decimal, Decimal, Decimal]:
        """Returns (dim1, dim2, dim3) in ascending order for boundary comparison."""
        return tuple(sorted([self.length, self.width, self.height]))  # type: ignore


@dataclass(frozen=True)
class PlacementDTO:
    """Represents the exact 3D spatial position and orientation of a placed item."""
    item_id: str
    sku: str
    name: str
    x: Decimal
    y: Decimal
    z: Decimal
    dx: Decimal  # Dimension along X in this rotation
    dy: Decimal  # Dimension along Y in this rotation
    dz: Decimal  # Dimension along Z in this rotation

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "sku": self.sku,
            "name": self.name,
            "x": float(self.x),
            "y": float(self.y),
            "z": float(self.z),
            "dx": float(self.dx),
            "dy": float(self.dy),
            "dz": float(self.dz),
        }


@dataclass
class PackingResultDTO:
    """Comprehensive outcome of testing an order against a specific box."""
    is_feasible: bool
    box: Optional[BoxDTO] = None
    placed_items: List[PlacementDTO] = field(default_factory=list)
    unplaced_items: List[ItemDTO] = field(default_factory=list)
    volume_utilization_pct: Decimal = Decimal("0.00")
    weight_utilization_pct: Decimal = Decimal("0.00")
    execution_time_ms: int = 0
    failure_reason: str = ""


@dataclass
class BoxEvaluationSummary:
    """Structured audit record of evaluating an order against a candidate box."""
    box_id: int
    box_name: str
    packaging_cost: Decimal
    is_active: bool
    is_feasible: bool
    rejection_reason: str = ""
    weight_feasible: bool = True
    volume_feasible: bool = True
    dimensional_feasible: bool = True
    spatial_feasible: bool = True
    volume_utilization_pct: Decimal = Decimal("0.00")
    weight_utilization_pct: Decimal = Decimal("0.00")
    packing_result: Optional[PackingResultDTO] = None
