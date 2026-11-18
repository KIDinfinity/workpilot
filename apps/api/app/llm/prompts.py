"""版本化 prompt 加载器。

约定：`prompts/<name>.v<N>.md`，文件首部是 YAML front matter（id / version / model /
changelog），正文用 `{变量名}` 占位。代码只按 `id.vN` 引用，改 prompt = 新增版本文件。

为什么不用 `str.format`：prompt 正文里一旦出现 JSON 示例的 `{`，`format` 会把它当成
占位符直接报 KeyError / ValueError；这里只替换 `{标识符}` 形式的占位符。
"""

import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from app.core.config import get_settings

_FM = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
_VAR = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")  # 只匹配 {标识符}，{"a": 1} 不受影响


@dataclass(frozen=True)
class Prompt:
    id: str
    version: str
    model: str
    body: str

    @property
    def ref(self) -> str:
        """用于日志 / 响应 / 评测报告的稳定引用，如 `structured_answer.v1`。"""
        return f"{self.id}.v{self.version}"

    def render(self, **values: object) -> str:
        missing = set(_VAR.findall(self.body)) - values.keys()
        if missing:
            raise KeyError(f"prompt {self.ref} 缺少变量: {sorted(missing)}")
        return _VAR.sub(lambda m: str(values[m.group(1)]), self.body)


@lru_cache
def load_prompt(name: str) -> Prompt:
    """name 形如 `structured_answer.v1`（不带 .md）。进程内缓存，改 prompt 需重启。"""
    path = get_settings().prompts_dir / f"{name}.md"
    m = _FM.match(path.read_text(encoding="utf-8"))
    if not m:
        raise ValueError(f"{path} 缺少 front matter")
    meta = yaml.safe_load(m.group(1))
    return Prompt(
        id=meta["id"],
        version=str(meta["version"]),
        model=meta.get("model", ""),
        body=m.group(2).strip(),
    )
