# =============================================================================
# [1] 라이브러리 임포트 (가장 먼저!)
# =============================================================================
import datetime as dt
from collections import Counter
from datetime import datetime
from korean_lunar_calendar import KoreanLunarCalendar
import saju_constants as sc


# =============================================================================
# [3] 유틸리티 & 헬퍼 함수 (재료 손질)
# - 다른 함수들이 갖다 쓰는 기초 기능들입니다.
# =============================================================================

# 3-1. 십성 추출
def get_ten(my_gan, target_char, is_gan=True):

    if target_char in ['❔', '?', None, '']:
        return "알수없음"


    if my_gan not in sc.GAN_DATA:
        return "오류"

    my_ele = sc.GAN_DATA[my_gan][0] # 일간의 오행
    my_pm = sc.GAN_DATA[my_gan][1] # 일간의 음양

    # 타겟의 오행과 음양
    if is_gan:
        if target_char not in sc.GAN_DATA: return "알수없음"
        target_data = sc.GAN_DATA[target_char]
    else:
        if target_char not in sc.JI_DATA: return "알수없음"
        target_data = sc.JI_DATA[target_char]

    tgt_ele = target_data[0] # 타겟의 오행
    tgt_pm = target_data[1] # 타겟의 음양


    my_idx = sc.FIVE_ELEMENTS.index(my_ele) # 일간의 오행 인덱스
    tgt_idx = sc.FIVE_ELEMENTS.index(tgt_ele) # 타겟의 오행 인덱스
    rel_idx = (tgt_idx - my_idx + 5) % 5 # 인덱스 차이 계산

    final_pm = 0 if my_pm == tgt_pm else 1 # 음양 같은지 계산

    return sc.TEN_GODS[rel_idx][final_pm] # 십성 출력

# 3-2. 십성 카테고리 추출
def get_ten_category(term):
    category_map = {
        '비견': '비겁', '겁재': '비겁',
        '식신': '식상', '상관': '식상',
        '편재': '재성', '정재': '재성',
        '편관': '관성', '정관': '관성',
        '편인': '인성', '정인': '인성'
    }

    # 해당되면 분류를 반환, 없으면 '알 수 없음' 반환
    return category_map.get(term, "알 수 없음")

# 3-3. 오행에서 십성 추출
def get_ten_from_element(my_gan, target_element):

    my_ele = sc.GAN_DATA[my_gan][0] # 일간의 오행

    my_idx = sc.FIVE_ELEMENTS.index(my_ele) # 일간의 오행 인덱스
    tgt_idx = sc.FIVE_ELEMENTS.index(target_element) # 타겟의 오행 인덱스

    rel_idx = (tgt_idx - my_idx + 5) % 5 # 인덱스 차이 계산

    return sc.TEN_SORT[rel_idx] # 십성 종류 출력

# 3-6. 천간 지지 합충 십성 관계 해석 글 추출
def get_interaction_desc(type_name, ten1, ten2):
    key = f"{ten1}_{ten2}" # 예: "상관_정관"

    target_db = None
    if type_name == "천간합": target_db = sc.GAN_HAP_DB
    elif type_name == "천간충": target_db = sc.GAN_CHUNG_DB
    elif type_name == "지지합": target_db = sc.JI_HAP_DB
    elif type_name == "지지충": target_db = sc.JI_CHUNG_DB

    if target_db:
        return target_db.get(key, f"{ten1}과 {ten2}의 {type_name} 작용")
    return ""


# =============================================================================
# [4] 만세력 날짜 계산 (엔진)
# - 날짜를 넣으면 간지를 뱉어주는 함수
# =============================================================================
# 문자열 날짜 입력
def date_luck(date_input):

    f_year = 1984
    f_month_y, f_month_m = 1923, 12
    f_day = dt.datetime(1899, 12, 22)

    diff = 0

    if len(date_input) == 4:
        d = int(date_input)
        result = f"{d}년"

        diff = d - f_year
    elif len(date_input) == 6:
        d = dt.datetime.strptime(date_input, "%Y%m")
        result = f"{d.year}년 {d.month}월"

        diff_before_y = d.year - f_month_y
        diff_before_m = d.month - f_month_m
        diff = diff_before_y*12 + diff_before_m
    elif len(date_input) == 8:
        d = dt.datetime.strptime(date_input, "%Y%m%d")
        week_list = ["월", "화", "수", "목", "금", "토", "일"]
        week_idx = d.weekday() # 0~6 사이 숫자 나옴
        week_char = week_list[week_idx] # 숫자를 한글로 변환
        result = f"{d.year}년 {d.month}월 {d.day}일 ({week_char})"

        diff_before = d - f_day
        diff = diff_before.days

    g = diff % 10
    j = diff % 12
    luck_gan = sc.GAN[g]
    luck_ji = sc.JI[j]


    return result , f"{luck_gan}{luck_ji}"

# 양력/음력
def get_solar_date(birth_input_str, cal_type):

    date_input_d = dt.datetime.strptime(birth_input_str, "%Y%m%d")
    y, m, d = date_input_d.year, date_input_d.month, date_input_d.day

    # 1. 양력
    if cal_type == 'solar' or not cal_type:
        return y, m, d

    # 2. 음력/윤달 처리
    calendar = KoreanLunarCalendar()
    # cal_type이 'lunar_leap'이면 True(윤달), 아니면 False(평달)
    is_leap = (cal_type == 'lunar_leap')

    try:
        # 음력 날짜 설정 -> 자동으로 양력 변환됨
        calendar.setLunarDate(y, m, d, is_leap)
        return calendar.solarYear, calendar.solarMonth, calendar.solarDay
    except Exception:
        # 변환 에러 시 안전하게 입력값 그대로 반환
        return y, m, d

# =============================================================================
# [5] 핵심 분석 로직 (요리 과정)
# - 테마, 세력전, 12운성 등 개별 분석 함수들
# =============================================================================
class SajuAnalyzer:
    def __init__(self, full_saju, luck_ganji):
        """
        full_saju: ['갑', '인', ...] 형태의 리스트
        luck_ganji: ['갑', '인'] 형태의 리스트
        """
        self.full_saju = full_saju
        self.luck_ganji = luck_ganji

    # 3-4. 운 십성 추출
    def luck_ten(self):

        my = self.full_saju[4]

        g = get_ten(my, self.luck_ganji[0], is_gan=True)
        j = get_ten(my, self.luck_ganji[1], is_gan=False)

        # 계산기 ①번 사용
        return g, j

    # 3-5. 운의 관계 해석 추출
    def get_luck_combination_desc(self):

        gan_ten, ji_ten = self.luck_ten()

        messages = []
        total = []

        key = f"{gan_ten}_{ji_ten}"

        messages.append(f"[운] {gan_ten}과 {ji_ten}의 기운이 함께 들어옵니다.")
        t = sc.LUCK_COMBINATION_DB.get(key)
        total.append(f"{t}")

        return messages, total

    # 3-7. 공망 파악
    def get_gongmang(self): # 공망 여부 함수
        g = self.full_saju[4]
        j = self.full_saju[5]

        gan_idx = sc.GAN.index(g)
        ji_idx = sc.JI.index(j)

        diff = (ji_idx - gan_idx + 12) % 12

        GONGMANG_MAP = {
            0: ['술', '해'],  # 갑자순 (차이 0) -> 끝 번호
            2: ['자', '축'],  # 갑인순 (차이 2) -> 0, 1번
            4: ['인', '묘'],  # 갑진순 (차이 4) -> 2, 3번
            6: ['진', '사'],  # 갑오순 (차이 6) -> 4, 5번
            8: ['오', '미'],  # 갑신순 (차이 8) -> 6, 7번
            10: ['신', '유']  # 갑술순 (차이 10) -> 8, 9번
        }

        return GONGMANG_MAP[diff]



    # 5-1. 격돌 파악
    def check_group_battle(self):

        my_ji = self.full_saju[1:8:2]
        luck_ji = self.luck_ganji[1]

        total_ji = my_ji + [luck_ji]
        counts = Counter(total_ji)


        msgs = []
        tots = []

        for pair_set, title, risk_detail in sc.CHUNG_PAIRS:
            p1, p2 = list(pair_set)
            c1 = counts[p1]
            c2 = counts[p2]

            if c1 > 0 and c2 > 0 and (c1 + c2 >= 3):

                # --- 승패 판정 (공통) ---
                if c1 > c2:
                    status = f"('{p1}' 세력이 우세하여 파괴력이 큽니다)"
                elif c2 > c1:
                    status = f"('{p2}' 세력이 우세하여 파괴력이 큽니다)"
                else:
                    status = f"(두 세력이 팽팽하게 맞붙어 끝장을 보는 형국입니다)"

                # --- 심각도 (공통) ---
                severity = "[위험]"
                if c1 + c2 >= 4: severity = "[대격돌]"
                if c1 + c2 >= 5: severity = "[재난급 충돌]"

                # ---------------------------------------------------------
                # ★ [핵심] 운의 개입 여부에 따른 문장 조립 (분기 처리)
                # ---------------------------------------------------------
                final_desc = ""

                # Case A: 운이 도화선인 경우 (사건 터짐) -> 설명 먼저!
                if luck_ji in pair_set:
                    final_desc = (
                        f"{title} {risk_detail}이 발생할 수 있습니다. {status}\n"
                        f"   [발동] 잠재되어 있던 화약고에 운({luck_ji})이 불을 붙였습니다! "
                        f"평소보다 충격이 훨씬 크니 당장 대비해야 합니다."
                    )

                # Case B: 원래 사주가 그런 경우 (만성) -> 경고 먼저, 설명은 괄호로 약하게
                else:
                    final_desc = (
                        f"{title} 사주 원국 자체에 충돌이 내재되어 있습니다. {status}\n"
                        f"   [만성적 주의] 운과 관계없이 늘 안고 가는 약점입니다. "
                        f"평소에 [{risk_detail}] 관련하여 꾸준한 관리가 필요합니다."
                    )

                msgs.append(f"{severity} {p1}({c1}) vs {p2}({c2}) 세력 충돌!")
                tots.append(final_desc)

        return msgs, tots

    # 5-2, 삼합, 반합
    def check_samhap_banhap(self):

        my = self.full_saju[4]
        my_ji = self.full_saju[1:8:2] # 내 지지 4글자
        full_ji = my_ji + [self.luck_ganji[1]] # 내 지지 4글자 + 들어오는 지지 1글자
        my_set = set(full_ji)
        results = []
        total = []

        for key, info in sc.SAMHAP_GROUP.items():
            group = info['group'] # {'신', '자', '진'}
            result_ele = info['element'] # '수'
            name = info['name'] # '수국'

            match_count = len(group & my_set) # 그룹과 지지 5글자 교집합 구하기

            if self.luck_ganji[1] not in group: # 사주 자체의 삼합/반합은 반영 X
                continue

            ten_god = get_ten_from_element(my, result_ele) # '수'의 십성 카테고리
            desc = sc.SAMHAP_DESC.get(ten_god + "국", "세력이 형성됩니다.") # ex) 비겁국 : ~~ 설명
            ban_desc = sc.BANHAP_DESC.get(ten_god + "국", "세력이 형성됩니다.")

            # 3개 겹칩
            if match_count == 3:
                results.append(f"[삼합] {key} {name} 형성 => {result_ele}({ten_god}) 휙득")
                total.append(f"{desc}")

            # 2개만 있음
            elif match_count == 2 :
                matched_chars = list(group & my_set)
                results.append(f"[반합] '{key}' 중 {matched_chars}가 모여 {result_ele}({ten_god})의 기운이 강해집니다.")
                total.append(f"{ban_desc}")

        return results, total

    # 5-3. 방합
    def check_bang(self): # 방합 여부 함수

        my_gan = self.full_saju[4]
        my_ji = self.full_saju[1:8:2] # 내 지지 4글자
        full_ji = my_ji + [self.luck_ganji[1]] # 내 지지 4글자 + 들어오는 지지 1글자
        my_set = set(full_ji)
        results = []
        total = []

        for key, info in sc.BANGHAP_GROUP.items():
            group = info['group']
            result_ele = info['element']

            match_count = len(group & my_set) # 그룹과 지지 5글자 교집합 구하기

            if self.luck_ganji[1] not in group: # 사주 자체의 삼합/반합은 반영 X
                continue

            ten_god = get_ten_from_element(my_gan, result_ele)
            desc = sc.BANGHAP_DESC.get(key, result_ele +"세력이 형성됩니다.")

            # 3개 겹칩
            if match_count == 3:
                results.append(f"[방합] {key} 형성 => {result_ele}({ten_god}) 세력 확장")
                total.append(f"{desc}")


        return results, total

    # 5-4. 삼형살, 형살, 자형
    def check_hyeongsal_all(self):

        my_ji = self.full_saju[1:8:2]
        luck_ji = self.luck_ganji[1]

        luck_ji_ten = self.luck_ten()[1]
        luck_ji_cate = get_ten_category(luck_ji_ten)

        ten_advice = sc.HYEONG_TEN_DESC.get(luck_ji_cate, "")

        # 전체 지지 집합 (운 포함)
        total_ji_set = set(my_ji + [luck_ji])

        msgs = []
        tots = []

        # --- A. 삼형살 그룹 체크 (인사신, 축술미) ---
        for key, info in sc.SAMHYEONG_GROUP.items():
            group = info['group']
            name = info['name']

            # 운의 글자가 그룹에 없으면 패스
            if luck_ji not in group:
                continue

            match_count = len(group & total_ji_set)
            k = sc.DESC_DB.get(key)

            # 1. 3개 다 모임 (삼형살)
            if match_count == 3:
                msgs.append(f"[삼형살] 운({luck_ji})이 와서 '{key}' 삼형살({name})이 완성되었습니다!")
                tots.append(f"{k} 특히 {ten_advice}")

            # 2. 2개만 모임 (일반 형살)
            elif match_count == 2:
                # (1) 교집합 구하기 ({'사', '신'})
                matched_list = list(group & total_ji_set)

                # (2) ★ 핵심: 가나다순 정렬하여 키 생성 ("사신")
                # sorted()는 유니코드 순서로 정렬하므로 한글 가나다순과 일치합니다.
                key_sorted = "".join(sorted(matched_list))

                # (3) DB에서 설명 가져오기
                desc = sc.DESC_DB.get(key_sorted)

                if desc: # DB에 설명이 있는 경우만 출력
                    matched_str = ", ".join(matched_list)
                    msgs.append(f"[형살] 운({luck_ji})이 와서 [{matched_str}] 형살이 성립됩니다.")
                    tots.append(desc)

        # --- B. 자묘형 (따로 체크) ---
        if luck_ji in sc.JAMYO_GROUP:
            # 자묘형은 '자'와 '묘'가 모두 있어야 성립 (2개)
            if sc.JAMYO_GROUP.issubset(total_ji_set):
                msgs.append(f"[형살] 운({luck_ji})으로 인해 '자묘형(무례지형)'이 성립됩니다.")
                tots.append(sc.DESC_DB.get("묘자")) # 키를 '묘자'(가나다순)로 맞춰둠

        # --- C. 자형 (내 지지에 운 글자와 똑같은 게 있으면) ---
        if luck_ji in sc.SELF_HYEONG:
            if luck_ji in my_ji: # 내 사주에도 그 글자가 있다면
                msgs.append(f"[자형] 운에서 온 '{luck_ji}'가 내 지지와 겹쳐 스스로를 볶습니다.")
                tots.append(sc.DESC_DB.get(luck_ji * 2)) # 진진, 오오...

        return msgs, tots

    # 5-5 천간합 천간충 지지합 지지충 => 천충지충
    def check_hap_chung(self):

        my = self.full_saju[4]
        my_gan = self.full_saju[0:7:2]
        my_ji = self.full_saju[1:8:2]
        luck_gan = self.luck_ganji[0]
        luck_ji = self.luck_ganji[1]

        messages = []
        total = []

        loop_count = 4
        if '❔' in my_ji: # 지지 중에 물음표가 있으면
            loop_count = 3

        for i in range(loop_count):
            g =  my_gan[i]
            j = my_ji[i]
            p =  sc.PILLAR[i]

            my_gan_ten = get_ten(my, g, is_gan=True)
            my_ji_ten = get_ten(my, j, is_gan=False)
            luck_gan_ten = get_ten(my, luck_gan, is_gan=True)
            luck_ji_ten = get_ten(my, luck_ji, is_gan=False)

            ganchung = False
            jichung = False

            # 1. 천간 (합 -> 충 순서)
            if sc.GAN_HAP.get(g) == luck_gan:
                hap_ele = sc.HAP_RESULT.get(g + luck_gan)
                hap_gan = get_ten_from_element(my, hap_ele)

                total_msg = get_interaction_desc('천간합', my_gan_ten, luck_gan_ten)
                total_result_msg = sc.RESULT_DESC.get(hap_gan)

                messages.append(f"[천간합] {p} ({g}, {my_gan_ten}) + 운 ({luck_gan}, {luck_gan_ten}) => {hap_ele}({hap_gan})")
                total.append(f"{total_msg} 결과적으로 {total_result_msg}")

            elif sc.GAN_CHUNG.get(g) == luck_gan:
                total_msg = get_interaction_desc('천간충', my_gan_ten, luck_gan_ten)

                messages.append(f"[천간충] {p} ({g}, {my_gan_ten}) vs 운 ({luck_gan}, {luck_gan_ten})")
                total.append(f"{total_msg}")
                ganchung = True

            # 2. 지지 (육합 -> 충 순서)
            if sc.JI_HAP.get(j) == luck_ji:
                hap_ele = sc.HAP_RESULT.get(j + luck_ji)
                hap_ji = get_ten_from_element(my, hap_ele)

                total_msg = get_interaction_desc('지지합', my_ji_ten, luck_ji_ten)
                total_result_msg = sc.RESULT_DESC.get(hap_ji)

                messages.append(f"[육합] {p} ({j}, {my_ji_ten}) + 운 ({luck_ji}, {luck_ji_ten}) => {hap_ele}({hap_ji})")
                total.append(f"{total_msg} 결과적으로 {total_result_msg}")

            elif sc.JI_CHUNG.get(j) == luck_ji:
                total_msg = get_interaction_desc('지지충', my_ji_ten, luck_ji_ten)

                messages.append(f"[지충] {p} ({j}, {my_ji_ten}) vs 운 ({luck_ji}, {luck_ji_ten})")
                total.append(f"{total_msg}")
                jichung = True

            if ganchung and jichung:
                messages.append(f"[천충지충] {p}가 완전히 깨졌습니다.")
                d = sc.CCJC_PILLAR_DESC.get(p)
                gt = get_ten_category(my_gan_ten)
                jt = get_ten_category(my_ji_ten)

                if gt == jt:
                    d1 = sc.CCJC_TEN_DESC.get(gt)
                    total.append(f"{d} 특히 {gt}({d1})에 타격이 집중됩니다. ")
                else:
                    d2 = sc.CCJC_TEN_DESC.get(gt)
                    d3 = sc.CCJC_TEN_DESC.get(jt)
                    total.append(f"{d}\n정신적으로는 {gt}({d2}), 현실적으로는 {jt}({d3}) 문제가 발생합니다")



        return messages, total

    # 5-6. 원진, 파, 해, 지지암합
    def check_minor(self):

        my = self.full_saju[4]
        my_ji = self.full_saju[1:8:2]
        luck_ji = self.luck_ganji[1]

        messages = []
        total = []

        loop_count = 4
        if '❔' in my_ji: # 지지 중에 물음표가 있으면
            loop_count = 3

        for i in range(loop_count):
            j = my_ji[i]
            p = sc.PILLAR[i]

            my_ji_ten = get_ten(my, j, is_gan=False)
            luck_ji_ten = get_ten(my, luck_ji, is_gan=False)

            # 키 생성 (가나다순)
            key_chars = sorted([j, luck_ji])
            key = "".join(key_chars)

            # 1. 원진
            if luck_ji in sc.JI_WONJIN.get(j, ""):
                messages.append(f"[원진] {p} ({j}, {my_ji_ten}) - 운 ({luck_ji}, {luck_ji_ten})")
                desc = sc.DESC_WONJIN.get(key)
                if desc and desc not in total: total.append(desc)

            # 2. 파
            if luck_ji in sc.JI_PA.get(j, ""):
                messages.append(f"[파] {p} ({j}, {my_ji_ten}) - 운 ({luck_ji}, {luck_ji_ten})")
                # ★ 핵심: 이제 파 전용 DB에서 가져옵니다!
                desc = sc.DESC_PA.get(key)
                if desc and desc not in total: total.append(desc)

            # 3. 해
            if luck_ji in sc.JI_HAE.get(j, ""):
                messages.append(f"[해] {p} ({j}, {my_ji_ten}) - 운 ({luck_ji}, {luck_ji_ten})")
                desc = sc.DESC_HAE.get(key)
                if desc and desc not in total: total.append(desc)

            # 4. 암합
            if sc.JI_AMHAP.get(j) == luck_ji:
                # (지장간 계산 로직 동일...)
                my_hidden = sc.JIJANGGAN.get(j, [])
                luck_hidden = sc.JIJANGGAN.get(luck_ji, [])

                for h1 in my_hidden:
                    for h2 in luck_hidden:
                        if sc.GAN_HAP.get(h1) == h2:
                            amhap_ele = sc.HAP_RESULT.get(h1 + h2)
                            amhap_ten = get_ten_from_element(my, amhap_ele)
                            amhap_hid_my_char = get_ten(my, h1, is_gan=True)
                            amhap_hid_luck_char = get_ten(my, h2, is_gan=True)

                            msg = f"[지지암합] {p} {j}(숨은 '{h1}', {amhap_hid_my_char}) + 운 {luck_ji}(숨은 '{h2}', {amhap_hid_luck_char}) -> 몰래 {amhap_ele}({amhap_ten}) 휙득"
                            messages.append(msg)

                            desc = sc.DESC_AMHAP.get(key)
                            if desc and desc not in total: total.append(desc)

        return messages, total

    # 5-7. 명암합
    def check_myong_amhap(self):

        my = self.full_saju[4]
        my_gan = self.full_saju[0:7:2]
        my_ji = self.full_saju[1:8:2]
        luck_gan = self.luck_ganji[0]
        luck_ji =self.luck_ganji[1]

        messages = []
        total = []

        loop_count = 4
        if '❔' in my_ji: # 지지 중에 물음표가 있으면
            loop_count = 3

        for i in range(loop_count):
            g = my_gan[i]
            j = my_ji[i]
            p = sc.PILLAR[i]

            my_hidden_list = sc.JIJANGGAN.get(j, []) # 내 지지 속에 숨은 글자들 ex) '진' 속 ['을', '계', '무']
            target_hidden = sc.GAN_HAP.get(luck_gan)     # 운의 천간이 원하는 짝꿍 ex) 경:을
            luck_gan_ten = get_ten(my, luck_gan, is_gan=True)
            target_ten = get_ten(my, target_hidden, is_gan=True)

            if target_hidden in my_hidden_list: # '을'이 ['을', '계', '무'] 속에 있음
                changed_ele = sc.HAP_RESULT.get(luck_gan + target_hidden) # 경을 : 금
                ten_category = get_ten_from_element(my, changed_ele) # 금의 십성은?

                desc = sc.MYONG_AMHAP_DB.get(ten_category, "은밀한 도움과 실속을 챙깁니다.")

                messages.append(f"[명암합] 운 천간 '{luck_gan}({luck_gan_ten})' + 내 {p} 지지 '{j}' 속 '{target_hidden}({target_ten})' => {changed_ele}({ten_category})")
                total.append(f"{desc}")

            # --- 로직 2: 내 천간(My Gan)이 운의 지지(Luck Ji) 속 지장간과 합을 하는가? ---
            luck_hidden_list = sc.JIJANGGAN.get(luck_ji, []) # 운의 지지 속에 숨은 글자들
            target_hidden_2 = sc.GAN_HAP.get(g)         # 내 천간이 원하는 짝꿍
            my_gan_ten = get_ten(my, g, is_gan=True)
            target_ten_2 = get_ten(my, target_hidden_2, is_gan=True)

            if target_hidden_2 in luck_hidden_list:
                changed_ele = sc.HAP_RESULT.get(g + target_hidden_2)
                ten_category = get_ten_from_element(my, changed_ele)

                desc = sc.MYONG_AMHAP_DB.get(ten_category, "의외의 곳에서 기회를 잡습니다.")

                messages.append(f"[명암합] 내 {p} 천간 '{g}({my_gan_ten})' ❤️ 운 지지 '{luck_ji}' 속 '{target_hidden_2}({target_ten_2})' => {changed_ele}({ten_category})")
                total.append(f"{desc}")

        return messages, total

    # 5-8. 귀인, 신살(역마살, 도화살, 화개살, 현침살)
    def check_sinsal(self):
        my_gan = self.full_saju[4] # 일간 (나) -> 천을귀인 보는 기준
        my_ji  = self.full_saju[5] # 일지 (내 몸) -> 역마/도화/화개 보는 기준

        luck_ji = self.luck_ganji[1] # 들어오는 운의 지지

        messages = []
        total = []


        for key, gan in sc.GWUIN_LOGIC.items():
            if luck_ji in gan.get(my_gan, set()):
                desc = sc.GWUIN_DESC.get(key)

                messages.append(f"[{key}] (운 '{luck_ji}' + 내 일간 '{my_gan}')")
                total.append(f"{desc}")

        for group, stars in sc.SINSAL_MAP.items():
            if my_ji in group: # 내 일지가 이 그룹에 속한다면
                t = sc.BASIC_SHINSAL_DB.get(luck_ji)

                if luck_ji == stars['역마']:
                    messages.append(f"{t}")
                    total.append(f"✈️ 분주한 이동 :: 몸이 바빠지는 날입니다. 여행이나 출장, 이사처럼 움직임이 많을수록 행운이 따릅니다.")

                elif luck_ji == stars['도화']:
                    messages.append(f"{t}")
                    total.append(f"🌸 시선 집중 :: 오늘따라 사람들이 나를 주목하네요. 숨겨진 매력을 마음껏 발산해보세요.")

                elif luck_ji == stars['화개']:
                    messages.append(f"{t}")
                    total.append(f"🎨 예술적 재능 :: 내면의 잠재력이 꽃피는 날입니다. 예술이나 창작 활동, 혹은 옛 인연과의 재회가 있을 수 있어요.")

                break # 그룹 찾았으면 그만

        if luck_ji in sc.HYUNCHIM_CHARS:
            t = sc.BASIC_SHINSAL_DB_H.get(luck_ji)
            messages.append(f"{t}")
            total.append(f"💉 예리한 감각 :: 집중력과 손재주가 좋아집니다. 다만 날카로운 말로 상처 주지 않도록 조심하세요.")

        return messages, total

    # 5-9. 귀문관살
    def check_gwimun(self): # 15. 귀문 여부 함수

        my = self.full_saju[4]          # 내 일간 (십성 기준)
        my_ji = self.full_saju[1:8:2]   # 내 지지 4글자
        luck_ji = self.luck_ganji[1]    # 운의 지지

        messages = []
        total = []

        loop_count = 4
        if '❔' in my_ji: # 지지 중에 물음표가 있으면
            loop_count = 3

        for i in range(loop_count):
            j = my_ji[i] # 내 지지 한 글자
            p = sc.PILLAR[i] # 기둥 이름

            # 1. 귀문관살 성립 여부 확인
            # 내 글자와 운의 글자를 합친 세트가 귀문 목록에 있는가?
            current_pair = {j, luck_ji}

            if current_pair in sc.GWIMUN_PAIRS:
                # 십성 계산
                my_ji_ten = get_ten(my, j, is_gan=False)
                luck_ji_ten = get_ten(my, luck_ji, is_gan=False)

                # DB 키 생성 (가나다순 정렬)
                key = "".join(sorted([j, luck_ji]))
                desc = sc.GWIMUN_DB.get(key)

                msg = f"[귀문관살] {p} ({j}, {my_ji_ten}) - 운 ({luck_ji}, {luck_ji_ten})"

                messages.append(msg)
                # 중복 방지하며 설명 추가
                if desc and desc not in total:
                    total.append(f"{desc}")

        return messages, total

    # 5-10. 십이운성
    def check_12unseong(self): # 16. 12운성 확인 함수

        my = self.full_saju[4]
        luck_ji = self.luck_ganji[1]

        state = sc.UNSEONG_DB.get(my, {}).get(luck_ji, "")
        desc = sc.UNSEONG_DESC_DB.get(state, "")

        messages = []
        total = []

        messages.append(f"[십이운성] 이번 달의 기운은 '{state}'입니다.")
        total.append(f"{desc}")

        return messages, total

    # 5-11. 3대 악살(백호대살, 괴강살, 양인살)
    def check_special_stars(self):
        luck_str = "".join(self.luck_ganji) # ['갑', '진'] -> "갑진"

        msgs = []
        tots = []

        if luck_str in sc.BAEKHO:
            msgs.append(f"[백호대살] 강렬한 에너지가 들어옵니다.")
            tots.append(f"🐯 폭발적인 에너지 :: 호랑이 같은 기운이 솟아나요! 집중력이 좋아져 큰 성과를 낼 수 있지만, 급하게 움직이다 다치지 않게 조심하세요.")

        if luck_str in sc.GOEGANG:
            msgs.append(f"[괴강살] 우두머리의 기운이 들어옵니다.")
            tots.append(f"🦍 우두머리 리더십 :: 총명하고 결단력이 강해집니다. 남들을 압도하는 카리스마가 있지만, 너무 내 고집만 피우면 마찰이 생길 수 있어요.")

        if luck_str in sc.YANGIN:
            msgs.append(f"[양인살] 칼을 든 장수의 기운입니다.")
            tots.append(f"🗡️ 승부사 기질 :: 칼을 든 장수처럼 기세가 등등하네요. 경쟁에서 이기는 힘이 강력하지만, 지나친 자신감은 자제하고 건강을 챙기세요.")

        return msgs, tots


    # =============================================================================
    # [6] 종합 및 정렬 (플레이팅)
    # =============================================================================

    # 6-1. 상호작용 종합 함수
    def total_interactions(self):

        luck_ji = self.luck_ganji[1]

        messages = []
        total = []

        # 5번 함수들
        funcs = [
            self.check_group_battle, self.check_samhap_banhap, self.check_bang,
            self.check_hyeongsal_all, self.check_hap_chung, self.check_minor,
            self.check_myong_amhap, self.check_sinsal, self.check_gwimun,
            self.check_12unseong, self.check_special_stars
        ]

        for func in funcs:
            m, t = func() # 각 함수 실행
            messages.extend(m)
            total.extend(t)

        # 운의 십성
        m_luck, t_luck = self.get_luck_combination_desc()
        messages.extend(m_luck)
        total.extend(t_luck)

        # 공망 확인
        if luck_ji in self.get_gongmang():

            # ★ 핵심: 리스트 안에 있는 글자들을 하나로 합쳐서 검사해야 함!
            combined_msg = "".join(messages)

            if "[지충]" in combined_msg or "[육합]" in combined_msg:
                # 충이나 합으로 공망을 깨트림 (가장 좋음)
                messages.append("[완탈공]")
                total.append("🔓 위기 탈출 :: 막혀있던 운이 시원하게 뚫립니다! 비어있던 곳이 오히려 행운으로 채워지는 전화위복의 날이에요.")

            elif "[삼합]" in combined_msg or "[방합]" in combined_msg:
                # 강력한 합으로 공망을 무력화시킴
                messages.append("[탈공]")
                total.append("✨ 공망 해소 :: 든든한 합의 기운 덕분에 공망이 힘을 잃었네요. 걱정했던 일이 순조롭게 풀려나갑니다.")

            elif "형살]" in combined_msg:
                # 조정하면서 공망을 탈출함
                messages.append("[조정 탈공]")
                total.append("🔨 조정과 해결 :: 과정은 조금 시끄러울 수 있지만, 결국엔 해결됩니다. 고칠 건 고치고 넘어가면 오히려 결과가 좋아요.")

            elif "[반합]" in combined_msg or "[암합]" in combined_msg:
                # 약하게나마 공망을 해소함
                messages.append("[부분 탈공]")
                total.append("🌬️ 숨통 트임 :: 답답했던 흐름에 작은 구멍이 뚫리네요. 작지만 소중한 도움으로 실속을 챙길 수 있습니다.")

            elif "[원진]" in combined_msg or "[파]" in combined_msg or "[해]" in combined_msg or "[귀문]" in combined_msg:
                # 공망인데 예민함까지 더해짐 (주의)
                messages.append("[심리 공망]")
                total.append("🌧️ 마음 관리 :: 일이 좀처럼 손에 잡히지 않고 마음이 복잡해요. 억지로 하기보다 잠시 쉬어가는 게 상책입니다.")

            else:
                # 순수 공망
                messages.append("[공망]")
                total.append("🕳️ 채움의 시간 :: 노력 대비 성과가 적을 수 있어요. 욕심내지 말고 공부하거나 휴식하며 내공을 쌓으세요.")

        return messages, total

    # 6-2. 상호작용 정렬
    def sort_saju_results(self, messages, total):

        def get_rank(msg):
            for i, keyword in enumerate(sc.PRIORITY_KEYWORDS):
                if keyword in msg:
                    return i
            return 999

        # --- 정렬 실행 (필터링 로직 삭제함!) ---
        # messages와 total을 묶어서 정렬
        combined = list(zip(messages, total))
        combined.sort(key=lambda pair: get_rank(pair[0]))

        # --- 중복 해석(Description) 제거 ---
        # (내용이 완전히 똑같은 문장만 제거하고, 키워드가 다르면 살려둠)
        final_messages = []
        final_total = []
        seen_descriptions = set()

        for m, t in combined:
            if t not in seen_descriptions:
                final_messages.append(m)
                final_total.append(t)
                seen_descriptions.add(t)

        return final_messages, final_total


    # =============================================================================
    # [7] 최종 출력 (서빙)
    # - 외부에서(챗봇 등) 이 함수 하나만 부르면 되게 만듭니다.
    # =============================================================================
    # 수정 필요!
    def sectioned_saju_output(self, date_txt, format_for="kakao"):

        t1, t2 = self.total_interactions()
        sorted_msgs, sorted_tots = self.sort_saju_results(t1, t2)

        section_buckets = {title: [] for title in sc.SECTIONS}
        others = []

        # 1. 분류 (Categorizing) - 엄격한 매칭
        for msg, desc in zip(sorted_msgs, sorted_tots):
            is_matched = False
            for title, keywords in sc.SECTIONS.items():
                # msg 안에 키워드가 그대로 들어있는지 확인 (예: "[홍염살]" 안에 "[홍염"이 있는가?)
                if any(k in msg for k in keywords):
                    section_buckets[title].append(desc)
                    is_matched = True
                    break

            if not is_matched:
                others.append(desc)


        # 2. 텍스트 조립 (Formatting - 카카오톡 줄바꿈 스타일)
        final_text = f"📅 {date_txt} 운세\n"

        for title, descriptions in section_buckets.items():
            if not descriptions:
                continue

            # 섹션 제목 (위아래 공백으로 구분감 주기)
            final_text += f"\n{title}\n"

            for desc in descriptions:
                clean_desc = desc.strip()

                # DB 구조: "🤝 의기투합 :: 설명..."
                if "::" in clean_desc:
                    parts = clean_desc.split("::", 1)
                    keyword = parts[0].strip() # "🤝 의기투합"
                    content = parts[1].strip() # "설명..."

                    # ⭐ [디자인 포인트]
                    # ✔ 키워드 (엔터)
                    # 설명... (엔터)(엔터)
                    final_text += f"✔ {keyword}\n{content}\n\n"

                else:
                    # '::'가 없는 경우 (혹시 모를 예외 처리)
                    # 대괄호가 있다면 제거하고 보여줌
                    display_text = clean_desc.replace("[", "").replace("]", "")
                    final_text += f"✔ {display_text}\n\n"

        # 기타 사항
        if others:
            final_text += "\n💬 기타 참고사항\n"
            for desc in others:
                clean_desc = desc.strip()
                if "::" in clean_desc:
                    parts = clean_desc.split("::", 1)
                    keyword = parts[0].strip()
                    content = parts[1].strip()
                    final_text += f"✔ {keyword}\n{content}\n\n"
                else:
                    final_text += f"✔ {clean_desc}\n\n"

        return final_text.strip()

# endregion

# =============================================================================
# [8] 테스트 실행 블록 (Debug)
# - 이 파일을 직접 실행했을 때만 작동하는 코드
# =============================================================================
if __name__ == "__main__":
    # 1. 기초 데이터 준비
    test_saju = list("갑신무진계해정사")
    test_date = "20260103"

    # 2. 외부 함수를 이용해 운의 간지 추출 (재료 준비)
    date_txt, luck_ganji_str = date_luck(test_date)
    print(f"일진: {luck_ganji_str} ({date_txt})")

    luck_ganji = list(luck_ganji_str)

    # 3. ★ 핵심: 분석기(객체) 생성
    # 설계도(SajuAnalyzer)를 바탕으로 실제 분석기(analyzer)를 만듭니다.
    analyzer = SajuAnalyzer(test_saju, luck_ganji)


    t1, t2 = analyzer.total_interactions()
    sorted_msgs, sorted_tots = analyzer.sort_saju_results(t1, t2)

    # 4. 결과 출력
    # 이제 analyzer 가방 안에 데이터가 다 들어있으므로, 제목 텍스트만 넘겨줍니다.
    print("\n--- 결과 미리보기 ---\n")
    print(sorted_msgs)
    print(analyzer.sectioned_saju_output(date_txt))