"""DeepSeek（OpenAI 兼容接口）客户端封装。"""
from openai import OpenAI

from app import config


def analyze_country(country_code: str, project_type: str, profile_summary: str) -> str:
    """调用默认模型，基于风险画像生成国别风险分析文本。"""
    if not config.DEEPSEEK_API_KEY:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在 .env 中填写后重试")
    client = OpenAI(api_key=config.DEEPSEEK_API_KEY, base_url=config.DEEPSEEK_BASE_URL)
    response = client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是企业海外投资地缘政治风险分析师。请基于给定的国别风险画像，"
                    "面向出海企业海外业务负责人输出简明分析：核心风险、关键不确定性与初步应对建议。"
                    "区分事实与推断，并注明需要人工核实的事项。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"国家代码：{country_code}\n项目类型：{project_type}\n风险画像：\n{profile_summary}"
                ),
            },
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content or ""
