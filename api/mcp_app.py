from mcp.server.fastmcp import FastMCP
from datetime import datetime, timedelta
import converter
import saju_logic

# 1. MCP 서버 초기화
mcp = FastMCP("OunbiFortune")

@mcp.tool()
def get_daily_fortune(birth_date: str, birth_time: str = None, calendar_type: str = "solar") -> str:
    """
    사용자의 생년월일을 바탕으로 오늘 하루의 사주 운세를 분석합니다.
    
    Args:
        birth_date (str): 생년월일 8자리 (예: "20040414")
        birth_time (str, optional): 태어난 시간 4자리 (예: "1030"). 모를 경우 None.
        calendar_type (str): "solar"(양력), "lunar"(음력 평달), "lunar_leap"(음력 윤달)
    """
    try:
        # 1. 양력 변환 (음력일 경우 처리)
        real_y, real_m, real_d = saju_logic.get_solar_date(birth_date, calendar_type)
        
        # 2. 사주 8글자 계산
        f_hour = int(birth_time[:2]) if birth_time else None
        f_min = int(birth_time[2:]) if birth_time else 0
        user_saju_list = converter.get_sajupalja(real_y, real_m, real_d, f_hour, f_min)
        
        # 3. 오늘(KST)의 간지 정보 가져오기
        today_str = (datetime.now() + timedelta(hours=9)).strftime('%Y%m%d')
        date_txt, luck_ganji_str = saju_logic.date_luck(today_str)
        
        # 4. 분석 엔진 가동
        analyzer = saju_logic.SajuAnalyzer(user_saju_list, list(luck_ganji_str))
        
        # 5. 결과 텍스트 생성
        fortune_result = analyzer.sectioned_saju_output(date_txt)
        
        return f"분석 결과:\n{fortune_result}"

    except Exception as e:
        return f"운세를 분석하는 중 오류가 발생했습니다: {str(e)}"

if __name__ == "__main__":
    mcp.run()