import datetime as dt

# ====================================================
# [1] 기초 데이터
# ====================================================
GAN = list("갑을병정무기경신임계")
JI = list("자축인묘진사오미신유술해")

# ====================================================
# [2] 절기 기준일 (월별 보정값)
# ====================================================
JEOLGI_DATE = {
    1: 6,   # 소한 (1월)
    2: 4,   # 입춘 (2월) - ★ 띠가 바뀌는 기준
    3: 6,   # 경칩 (3월)
    4: 5,   # 청명 (4월)
    5: 6,   # 입하 (5월)
    6: 6,   # 망종 (6월)
    7: 7,   # 소서 (7월)
    8: 8,   # 입추 (8월)
    9: 8,   # 백로 (9월)
    10: 8,  # 한로 (10월)
    11: 7,  # 입동 (11월)
    12: 7   # 대설 (12월)
}

# ====================================================
# [3] 사주팔자 구하기
# ====================================================
def get_sajupalja(year, month, day, hour=None, minute=0):

    if minute is None: minute = 0
    target_date = dt.datetime(year, month, day)

    # ------------------------------------------------
    # [3-1. 년주 계산] 입춘(2월 4일) 기준
    # ------------------------------------------------
    saju_year = year
    cutoff = JEOLGI_DATE[month]

    # 1월이거나, 2월인데 입춘 전이면 -> 작년으로 계산
    if month < 2 or (month == 2 and day < cutoff):
        saju_year = year - 1

    # 년주 뽑기
    y_diff = saju_year - 1984
    y_gan_idx = (y_diff) % 10
    y_ji_idx = (y_diff) % 12

    while y_gan_idx < 0: y_gan_idx += 10
    while y_ji_idx < 0: y_ji_idx += 12

    year_gan = GAN[y_gan_idx]
    year_ji = JI[y_ji_idx]

    # ------------------------------------------------
    # [3-2. 월주 계산] ★ 여기가 핵심 수정됨!
    # ------------------------------------------------

    # 1. 현재 월이 절기를 지났는지 확인
    # day < cutoff 이면 '전 달'로 간주
    month_cursor = month
    if day < cutoff:
        month_cursor = month - 1
        if month_cursor == 0: month_cursor = 12

    # 2. 월지(지지) 인덱스 매핑
    # 12(자), 1(축), 2(인), 3(묘) ...
    m_ji_idx = month_cursor % 12

    # 3. 월간(천간) 계산 (년두법)
    # 기준: 그 해의 첫 달인 '인월(2)'의 천간을 먼저 구함
    # 공식: (년간idx % 5 + 1) * 2
    start_gan_idx = (y_gan_idx % 5 + 1) * 2

    # [수정된 로직] 인월(2)로부터 몇 달이나 지났는지 계산
    # 인(2) -> 0칸
    # 묘(3) -> 1칸
    # ...
    # 자(0) -> 10칸 (연말)
    # 축(1) -> 11칸 (연말)

    if m_ji_idx >= 2:
        dist = m_ji_idx - 2
    else:
        # 자(0), 축(1)은 인(2)보다 인덱스는 작지만, 실제로는 해의 끝자락임
        dist = m_ji_idx + 10

    m_gan_idx = (start_gan_idx + dist) % 10

    month_gan = GAN[m_gan_idx]
    month_ji = JI[m_ji_idx]

    # ------------------------------------------------
    # [3-3. 일주 계산]
    # ------------------------------------------------
    base_date = dt.datetime(1900, 1, 1) # 갑술
    days_diff = (target_date - base_date).days

    d_gan_idx = (0 + days_diff) % 10
    d_ji_idx = (10 + days_diff) % 12

    day_gan = GAN[d_gan_idx]
    day_ji = JI[d_ji_idx]

    # ------------------------------------------------
    # [3-4. 시주 계산]
    # ------------------------------------------------
    if hour is None:
        time_gan = "❔"
        time_ji = "❔"
    else:
        time_val = hour + (minute / 60)

        # 자시(23:30 ~ 01:29)
        if time_val >= 23.5 or time_val < 1.5:
            t_ji_idx = 0
        else:
            t_ji_idx = int((time_val - 1.5) / 2) + 1
        t_ji_idx %= 12

        # 시두법
        t_start_gan = (d_gan_idx % 5) * 2
        t_gan_idx = (t_start_gan + t_ji_idx) % 10

        time_gan = GAN[t_gan_idx]
        time_ji = JI[t_ji_idx]

    return [year_gan, year_ji, month_gan, month_ji, day_gan, day_ji, time_gan, time_ji]
