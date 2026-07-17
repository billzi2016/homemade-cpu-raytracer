"""生产渲染器的数学、物理和统计验证公开接口。"""

from renderer.validation.energy import validate_material_energy
from renderer.validation.white_furnace import WhiteFurnaceResult, run_white_furnace

__all__ = ["WhiteFurnaceResult", "run_white_furnace", "validate_material_energy"]
