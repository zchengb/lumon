"""Conservative recognition of explicit publication holds and resume commands."""

import re

from lumon.tools.steering import SteeringPolicy

_ACTION = r"(?:commit|push|deploy|merge|publish|提交|推送|部署|合併|合并|發布|发布)"
_HOLD = (
    r"(?:不要|不准|禁止|先不|暫不|暂不|先別|先别|別再|别再|暫停|暂停|停止|取消|"
    r"\b(?:don't|do\s+not|stop|pause|hold|not\s+yet|no)\b)"
)
_PUBLICATION_HOLD = re.compile(
    rf"(?:{_HOLD}[^\n.!?。！？]{{0,40}}{_ACTION}|{_ACTION}[^\n.!?。！？]{{0,24}}{_HOLD})",
    re.IGNORECASE,
)
_STOP = re.compile(
    r"^(?:stop|pause|cancel|停止|暫停|暂停|先停一下|先停下|先等等|等一下)[\s.!。！]*$",
    re.IGNORECASE,
)


def steering_policy(text: str) -> SteeringPolicy | None:
    if re.match(r"^\s*/resume(?:\s|$)", text, re.IGNORECASE):
        return "resume"
    if re.match(r"^\s*/pause(?:\s|$)", text, re.IGNORECASE):
        return "pause"
    if _STOP.fullmatch(text.strip()) or _PUBLICATION_HOLD.search(text):
        return "pause"
    return None
