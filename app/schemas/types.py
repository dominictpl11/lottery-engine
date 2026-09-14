"""Schema 层共用的标注类型。"""

from typing import Annotated

from pydantic import AwareDatetime, BeforeValidator

from app.core.timeutil import from_db

# 出参用的 UTC 时间。
#
# 库里存的是 naive UTC（§4.4），直接声明成 AwareDatetime 会在序列化时校验失败，
# 所以先用 from_db 补上 tzinfo 再校验。这样 API 对外始终是带偏移的 ISO 8601，
# 而库内表示保持 naive。
UtcDatetime = Annotated[AwareDatetime, BeforeValidator(from_db)]
