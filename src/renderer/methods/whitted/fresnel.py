"""介质界面的 Fresnel-Schlick 能量近似。"""

import math


def schlick_reflectance(cosine: float, incident_ior: float, transmitted_ior: float) -> float:
    """返回非偏振介质反射比例近似值。

    参数:
        cosine: 入射方向与朝向入射介质法线的余弦绝对值，范围 ``[0, 1]``。
        incident_ior/transmitted_ior: 界面两侧有限正折射率。
    返回值:
        范围 ``[0, 1]`` 的标量反射权重；透射权重为 ``1 - result``。
    异常:
        ValueError: 参数越界、非有限或折射率非正时抛出。
    副作用:
        无。
    """

    if not math.isfinite(cosine) or not 0.0 <= cosine <= 1.0:
        raise ValueError("cosine 必须位于 [0, 1]")
    if not math.isfinite(incident_ior) or not math.isfinite(transmitted_ior):
        raise ValueError("折射率必须是有限数值")
    if incident_ior <= 0.0 or transmitted_ior <= 0.0:
        raise ValueError("折射率必须为正数")
    r0 = ((incident_ior - transmitted_ior) / (incident_ior + transmitted_ior)) ** 2
    return float(r0 + (1.0 - r0) * (1.0 - cosine) ** 5)
