from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from cryptography.fernet import Fernet # 양방향 암호화
import saju_logic  # saju_logic.py 불러오기
import converter   # [핵심] converter.py 불러오기
import sqlite3
import hashlib


# 시크릿키
app = Flask(__name__)
app.secret_key = 'eid2-ksbv3-0djes4'
app.permanent_session_lifetime = timedelta(minutes=60) # ✅ 1시간 유지 설정

def generate_security_token(eid):
    return hashlib.sha256((eid + app.secret_key).encode()).hexdigest()


# 암호화 키
FERNET_KEY = b'gRfXjF2553vMWDw-mTAX1h6DCaKHZN2Vj3xl3HogyTo='
cipher_suite = Fernet(FERNET_KEY)

def encrypt_id(uid):
    return cipher_suite.encrypt(uid.encode()).decode()

def decrypt_id(eid, ttl=None):
    try:
        # ttl이 있으면 검사하고, 없으면 그냥 복호화
        return cipher_suite.decrypt(eid.encode(), ttl=ttl).decode()
    except Exception:
        return None

# DB 초기화 함수 정의 (이 부분이 반드시 호출보다 위에 있어야 합니다)
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # 12개 컬럼 구조 반영
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,    -- 0
            name TEXT,                   -- 1
            phone TEXT,                  -- 2
            birth_date TEXT,             -- 3
            birth_time TEXT,             -- 4
            gender TEXT,                 -- 5
            calendar_type TEXT,          -- 6
            noti_time TEXT,              -- 7
            subscription_end TEXT,       -- 8
            is_early INTEGER DEFAULT 0,  -- 9
            password TEXT,               -- 10
            is_subscribed TEXT           -- 11
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ DB 초기화 완료!")

# 함수 호출 (정의가 끝난 후 실행)
init_db()


# --------------------------------------------------------------------------------
# 함수 정의
# --------------------------------------------------------------------------------
# [Helper 1] DB에서 유저 정보 가져오기
def get_user_data(uid):
    db_path = '/home/huhihhuh/users.db' # 절대 경로 사용
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (uid,))
    user = c.fetchone()
    conn.close()
    return user

# [Helper 2] 구독 권한 및 남은 기간 계산
def check_subscription(user):
    today_str = (datetime.now() + timedelta(hours=9)).strftime('%Y-%m-%d')
    sub_end = user['subscription_end'] if user['subscription_end'] else "1900-01-01"
    trial_end = user['is_subscribed'] if user['is_subscribed'] else "1900-01-01"

    is_active = (today_str <= sub_end) or (today_str <= trial_end)
    remain_date = max(sub_end, trial_end)
    return is_active, remain_date

# [Helper 3] 카카오톡 1000자 분할 및 응답 생성
def send_kakao_response(full_message):
    outputs = []
    if len(full_message) <= 1000:
        outputs.append({"simpleText": {"text": full_message}})
    else:
        # 안전한 분할 지점 찾기
        split_idx = full_message.rfind('\n\n', 0, 950)
        if split_idx == -1: split_idx = 900
        outputs.append({"simpleText": {"text": full_message[:split_idx].strip()}})
        outputs.append({"simpleText": {"text": f"(이어서)\n{full_message[split_idx:].strip()[:950]}"}})

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": outputs,
            "quickReplies": [
                {"action": "message", "label": "🏠 처음으로", "messageText": "🏠 처음으로"},
                {"action": "message", "label": "💡 자주 묻는 질문", "messageText": "💡 자주 묻는 질문" }]
        }
    })

# [Helper 4] 유저의 8글자 리스트를 한 번에 가져오는 함수
def get_user_saju_list(user):
    # 1. 생일 가공 및 양력 변환
    birth_str = str(user['birth_date'])
    real_b_y, real_b_m, real_b_d = saju_logic.get_solar_date(birth_str, user['calendar_type'])

    # 2. 시간 가공
    f_hour = int(str(user['birth_time']).zfill(4)[:2]) if user['birth_time'] else None
    f_min = int(str(user['birth_time']).zfill(4)[2:]) if user['birth_time'] else None

    # 3. 8글자 리스트 반환
    return converter.get_sajupalja(real_b_y, real_b_m, real_b_d, f_hour, f_min)




# ---------------------------------------------------------
# 1. join_gate : 회원가입 전 eid 포함 링크
@app.route('/join_gate')
def join_gate():
    eid = request.args.get('eid')
    skey = request.args.get('skey')

    # 1. 유효시간(1분) 체크 & 복호화
    # (주의: decrypt_id 함수에 ttl 기능이 추가되어 있어야 합니다!)
    uid = decrypt_id(eid, ttl=60)

    # 2. 보안 토큰 검사
    if not uid or skey != generate_security_token(eid):
        return "🚨 가입 링크 유효시간(1분)이 만료되었습니다. 챗봇에서 다시 버튼을 눌러주세요.", 403

    # 3. 신분증을 세션에 숨기기 (손목 밴드 발급)
    session['signup_uid'] = uid

    # 4. 깨끗한 가입 페이지로 이동! (URL 세탁)
    # 아까 가입/수정을 분리하기로 했으니 '/signup_page'로 보냅니다.
    return redirect('/signup_page')


# ---------------------------------------------------------
# 1-1. 회원가입 페이지 전용 함수
@app.route('/signup_page')
def signup_page():
    # 1. 보안 검사: join_gate를 거쳐서 '손목 밴드(세션)'를 차고 왔나요?
    if 'signup_uid' not in session:
        return """
        <script>
            alert('🚨 잘못된 접근입니다. 챗봇에서 다시 버튼을 눌러주세요.');
            window.close();
        </script>
        """, 403

    uid = session['signup_uid']
    user = get_user_data(uid)

    # 2. 이미 가입된 회원인지 확인 (친절함 포인트)
    # 이미 비밀번호까지 설정한 정회원이라면 -> 로그인 페이지로 안내
    if user and user['password'] and str(user['password']).strip() != "":
        return """
        <script>
            alert('이미 가입된 회원입니다! 로그인 페이지로 이동합니다. 🚗');
            location.href = '/login_page';
        </script>
        """

    # 3. 빈 데이터 껍데기 만들기 (HTML 에러 방지용)
    pre_data = {
        'name': '',
        'phone': '',
        'birth_date': '',
        'birth_time': '',
        'gender': 'female', # 기본값 선택
        'calendar': 'solar',
        'noti_time': '',
        'is_unknown': '',
        'is_early': ''
    }

    # 4. 가입 화면 보여주기
    # eid, skey는 이제 필요 없으니 전달하지 않습니다! (보안 UP)
    return render_template('signup.html', data=pre_data)

# ---------------------------------------------------------
# 1-2. DB에 정보를 저장하는 함수
@app.route('/submit_signup', methods=['POST'])
def submit_signup():

    # 1. 보안 검사 (손목 밴드 확인)
    if 'signup_uid' not in session:
        return "🚨 세션이 만료되었습니다. 챗봇에서 다시 시도해주세요.", 403

    uid = session['signup_uid'] # 세션에서 안전하게 ID 꺼내기



    # 2. 폼 데이터 받기 (HTML에서 보낸 내용)
    name = request.form.get('name')
    phone = request.form.get('phone')
    password = request.form.get('password')
    birth_date = request.form.get('birth_date')
    birth_time = request.form.get('birth_time')
    gender = request.form.get('gender')
    calendar_type = request.form.get('calendar_type')
    noti_time = request.form.get('noti_time')

    # 체크박스 값 처리
    is_early_val = request.form.get('is_early')
    is_early = 1 if is_early_val else 0

    is_unknown = request.form.get('unknown_time')

    # 태어난 시간 처리 (모름 체크시 NULL 저장)
    if is_unknown:
        db_birth_time = None
    else:
        db_birth_time = birth_time if birth_time else ""


    # 3. 비밀번호 암호화 (필수!)
    if not password or password.strip() == "":
        return """<script>alert('비밀번호를 입력해주세요!'); history.back();</script>"""

    final_password = generate_password_hash(password)


    # 4. DB에 저장 (INSERT)
    conn = sqlite3.connect('/home/huhihhuh/users.db')
    cursor = conn.cursor()

    try:
        # 가입 시점에는 구독/체험 정보는 없음(NULL)
        subscription_end = None # 구독
        is_subscribed = None # 체험
        fail_count = 0

        # 이미 존재하는지 한번 더 체크 (중복 에러 방지)
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
        if cursor.fetchone():
             # 이미 있으면 덮어쓰기보다는 그냥 업데이트 (혹시 모를 충돌 대비)
             # 하지만 원칙적으로는 여기서 막거나 UPDATE로 돌리는게 맞지만,
             # 가입 로직이므로 일단 삭제 후 다시 넣거나 에러 처리
             pass

        # 데이터 삽입 쿼리
        cursor.execute("""
            INSERT OR REPLACE INTO users
            (user_id, name, phone, birth_date, birth_time, gender, calendar_type, noti_time, subscription_end, is_early, password, is_subscribed, fail_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, name, phone, birth_date, db_birth_time, gender, calendar_type, noti_time, subscription_end, is_early, final_password, is_subscribed, fail_count))

        conn.commit()

    except Exception as e:
        conn.close()
        return f"저장 중 오류가 발생했습니다: {str(e)}"

    conn.close()


    # 5. 가입 완료 페이지를 위해 사주 8글자 계산하기
    # get_user_saju_list 함수는 딕셔너리(user) 형태를 원하므로 임시로 만듭니다.
    temp_user = {
        'birth_date': birth_date,
        'birth_time': db_birth_time,
        'calendar_type': calendar_type
    }


    # 사주 8글자 뽑기 (converter.py 등 활용)
    try:
        saju_data = get_user_saju_list(temp_user)
    except:
        saju_data = ['?', '?', '?', '?', '?', '?', '?', '?'] # 혹시 에러나면 물음표

    if not db_birth_time:
        saju_data[6] = '❔' # 시천간 (시간 위)
        saju_data[7] = '❔' # 시지지 (시간 아래)



    # 6. 마무리 (세션 청소 & 완료 페이지 렌더링)
    # ---------------------------------------------------------
    session.pop('signup_uid', None)

    return render_template('subscribe_done.html',
                           name=name,
                           saju=saju_data,
                           is_update=False) # 가입이니까 False





# ---------------------------------------------------------
# 2. 메인 메뉴
@app.route('/main_menu', methods=['POST'])
def main_menu():
    try:
        req = request.get_json()
        uid = req['userRequest']['user']['id']
        user = get_user_data(uid)
        eid = encrypt_id(uid) # 진짜 ID를 가면으로 가림
        token = generate_security_token(eid) # 가면 쓴 ID를 기준으로 토큰 생성
        domain = "https://huhihhuh.pythonanywhere.com"
        join_url = f"{domain}/join_gate?eid={eid}&skey={token}"
        login_url = f"{domain}/login_page"


        # 1. 신규 유저라면 가입 카드 하나만 보냄
        if user is None:
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "basicCard": {
                                "title": "반가워요! 당신의 AI 사주 파트너, 오운비입니다 ☀️",
                                "description": "오운비는 인공지능과 정통 명리학을 결합해 당신의 하루 에너지를 분석해 드려요.\n\n나만을 위한 맞춤 운세 조언을 듣고 싶으신가요? 지금 바로 시작해 보세요!",
                                "thumbnail": {
                                    "imageUrl": "https://cdn.pixabay.com/photo/2016/11/29/05/45/astronomy-1867616_1280.jpg" # 신뢰감을 주는 우주/별자리 이미지
                                },
                                "buttons": [
                                    {
                                        "action": "webLink",
                                        "label": "📝 정보 입력하기",
                                        "webLinkUrl": join_url
                                    },
                                    {
                                        "action": "message",
                                        "label": "💬 오운비 서비스 소개",
                                        "messageText": "채널 소개" # 이 메시지가 '채널 소개' 블록을 실행하게 합니다.
                                    }
                                ]
                            }
                        }
                    ],
                    "quickReplies": [
                        { "action": "message", "label": "🏠 처음으로", "messageText": "🏠 처음으로" },
                        { "action": "message", "label": "💡 자주 묻는 질문", "messageText": "💡 자주 묻는 질문" },
                        {"action": "message", "label": "💬 1:1 문의하기", "messageText": "💬 1:1 문의하기"}
                    ]
                }
            })


        # 2. 기존 유저 파악
        card1 = {
            "title": f"안녕하세요, {user['name']}님!",
            "description": "오늘의 운세를 확인하거나 서비스를 관리하세요.",
            "thumbnail": {"imageUrl": "https://images.unsplash.com/photo-1582201942988-13e60e4556ee?auto=format&fit=crop&w=800&q=80"},
            "buttons": [
                {"action": "message", "label": "☀️ 오늘의 운세 보기", "messageText": "오늘의 운세"}
            ]
        }
        card2 = {
            "title": f"추가 기능을 이용하고 싶으신가요? ",
            "description": "지금 바로 홈페이지에서 확인해보세요! ",
            "thumbnail": {"imageUrl": "https://cdn.pixabay.com/photo/2017/08/30/01/05/milky-way-2695569_1280.jpg"},
            "buttons": [
                {"action": "webLink", "label": "😃 오운비 바로가기", "webLinkUrl": login_url}
            ]
        }


        # 3. 카로셀로 합쳐서 응답
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "carousel": {
                            "type": "basicCard",
                            "items": [card1, card2]
                        }
                    }
                ],
                "quickReplies": [
                    { "action": "message", "label": "🏠 처음으로", "messageText": "🏠 처음으로" },
                    {"action": "message", "label": "💡 자주 묻는 질문", "messageText": "💡 자주 묻는 질문"},
                    {"action": "message", "label": "💬 1:1 문의하기", "messageText": "💬 1:1 문의하기"}
                ]
            }
        })

    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"메뉴 로딩 오류: {str(e)}"}}]}})


# ---------------------------------------------------------
# 2-1. 오늘의 운세 기능
@app.route('/fortune_today', methods=['POST'])
def fortune_today():
    try:
        req = request.get_json()
        uid = req['userRequest']['user']['id']

        # 1. 유저 정보 및 권한 체크 (헬퍼 사용)
        user = get_user_data(uid)
        if not user: return get_register_card(uid, "https://huhihhuh.pythonanywhere.com")

        is_active, remain_date = check_subscription(user)
        user_name = user['name'] or "고객"

        # 2. 날짜 준비 (오늘)
        target_date_str = (datetime.now() + timedelta(hours=9)).strftime('%Y%m%d')
        date_txt, luck_ganji_str = saju_logic.date_luck(target_date_str) # 전처리

        # 3. 사주 데이터 생성
        user_saju_list = get_user_saju_list(user)

        # 4. 분석 엔진 가동 (클래스 사용!)
        analyzer = saju_logic.SajuAnalyzer(user_saju_list, list(luck_ganji_str))
        fortune_text = analyzer.sectioned_saju_output(date_txt) # 가공된 date_txt 주입

        # 5. 응답 전송
        remain_msg = f"✨ 프리미엄 이용 중 (~{remain_date})" if is_active else "📢 무료 회원 이용 중"
        full_message = f"🌟 {user_name}님, 반갑습니다! \n[{remain_msg}]\n\n{fortune_text}"

        return send_kakao_response(full_message)

    except Exception as e:
        return jsonify({"version": "2.0", "template": {"outputs": [{"simpleText": {"text": f"❌ 오류: {str(e)}"}}]}})






# ------------------------------------------------------------------
# 3-1. 로그인 페이지 보여주기
@app.route('/login_page')
def login_page():
    # 이미 로그인 된 상태라면? -> 바로 대시보드로 통과!
    if 'dashboard_auth' in session:
        return redirect('/dashboard')

    return render_template('login.html')

# ------------------------------------------------------------------
# 3-2.수동 로그인 검증 (전화번호 + 비밀번호)
@app.route('/verify_manual_login', methods=['POST'])
def verify_manual_login():
    phone = request.form.get('phone')
    input_pw = request.form.get('password')

    conn = sqlite3.connect('/home/huhihhuh/users.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. 전화번호로 유저 찾기
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    user = cursor.fetchone()

    # 유저가 없으면?
    if not user:
        conn.close()
        return """<script>alert('등록되지 않은 전화번호입니다.\\n챗봇에서 먼저 가입을 진행해주세요!'); history.back();</script>"""



    # 2. 계정 잠금 확인 (5회 오류 시)
    # (fail_count 컬럼이 없으면 0으로 취급)
    fail_count = user['fail_count'] if 'fail_count' in user.keys() else 0

    if fail_count >= 5:
        conn.close()
        return """
        <script>
            alert('🚨 비밀번호 5회 오류로 계정이 잠겼습니다.\\n개발자에게 문의하여 잠금을 해제해주세요.');
            history.back();
        </script>
        """



    # 3. 비밀번호 확인
    try: db_pw = user['password']
    except: db_pw = user[10] # 튜플 인덱스 대비

    # check_password_hash: 암호화된 비번 비교
    # db_pw == input_pw: 옛날(평문) 비번 비교 (호환성용)
    if check_password_hash(db_pw, input_pw) or db_pw == input_pw:
        # ✅ 로그인 성공!

        # 틀린 횟수 0으로 초기화
        cursor.execute("UPDATE users SET fail_count = 0 WHERE user_id = ?", (user['user_id'],))
        conn.commit()
        conn.close()

        # 세션 발급 (대시보드 입장권)
        session['dashboard_auth'] = user['user_id']
        session.permanent = True # 창 닫아도 유지 (설정에 따라 다름)

        # 정보수정 권한은 여기서 주지 않습니다 (대시보드 안에서 또 비번 쳐야 줌)
        session.pop('edit_auth', None)

        return redirect('/dashboard')

    else:
        # ❌ 로그인 실패!

        # 틀린 횟수 +1 증가
        cursor.execute("UPDATE users SET fail_count = fail_count + 1 WHERE user_id = ?", (user['user_id'],))
        conn.commit()
        conn.close()

        return f"""
        <script>
            alert('비밀번호가 일치하지 않습니다! ❌\\n(현재 {fail_count + 1}회 오류 / 5회 시 잠김)');
            history.back();
        </script>
        """

# ------------------------------------------------------------------
# 3-3. 대시보드
@app.route('/dashboard')
def dashboard():
    # 1. 로그인 여부 확인 (문지기)
    # 세션에 'dashboard_auth' 도장이 없으면 -> 로그인 페이지로 쫓아냄
    if 'dashboard_auth' not in session:
        return redirect('/login_page')

    uid = session['dashboard_auth']


    # 2. 유저 정보 가져오기
    user = get_user_data(uid)

    # 만약 세션은 있는데 DB에 유저가 없다? (삭제된 계정 등)
    # -> 세션 지우고 로그인 페이지로 보냄
    if not user:
        session.pop('dashboard_auth', None)
        return redirect('/login_page')


    # 3. 보안 강화: 정보수정 권한 회수
    # 대시보드에 돌아왔다는 건 수정을 마쳤거나 안 한다는 뜻이므로
    # '수정 권한(edit_auth)'은 여기서 뺏습니다. (다시 비번 쳐야 함)
    session.pop('edit_auth', None)



    # 4. 화면 표시 (구독 상태 체크 등)
    is_active, remain_date = check_subscription(user)
    return render_template('dashboard.html',
                           user=user,
                           is_active=is_active,
                           remain_date=remain_date)

# ------------------------------------------------------------------
# 3-4. 로그아웃
@app.route('/logout')
def logout():
    session.pop('dashboard_auth', None) # 입장권 찢기
    session.pop('edit_auth', None)      # 수정 권한도 찢기
    return redirect('/login_page')      # 로그인 페이지로 추방






# ---------------------------------------------------------
# 4-1. 비밀번호 없이 세션으로 바로 체험 신청
@app.route('/apply_trial')
def apply_trial():

    uid = session.get('dashboard_auth')

    if not uid:
        return jsonify({'error': '세션이 만료되었습니다. 다시 로그인해주세요.'})

    user = get_user_data(uid)

    # 2. 중복 신청 방어
    if user['is_subscribed'] is not None and user['is_subscribed'] != "":
        return "<script>alert('이미 체험권을 사용하셨습니다.'); history.back();</script>"

    # 3. 체험 기간 부여 (3일)
    trial_expire = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')

    conn = sqlite3.connect('/home/huhihhuh/users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_subscribed = ? WHERE user_id = ?", (trial_expire, uid))
    conn.commit()
    conn.close()

    # 4. 완료 후 대시보드로 복귀
    return f"""
    <script>
        alert('🎉 3일 무료 체험이 시작되었습니다!\\n만료일: {trial_expire}');
        location.href = '/dashboard?';
    </script>
    """






# ---------------------------------------------------------
# 5-1. 정보수정 전 비밀번호 확인
@app.route('/verify_password', methods=['POST'])
def verify_password():
    uid = session.get('dashboard_auth')
    input_pw = request.form.get('password')

    if not uid:
        return "🚨 세션이 만료되었습니다. 다시 로그인해주세요.", 403

    user = get_user_data(uid)
    if not user: return """<script>alert('존재하지 않는 회원입니다.'); history.back();</script>"""


    # [보안 1] 5회 체크
    fail_count = user['fail_count'] if 'fail_count' in user.keys() else 0

    if fail_count >= 5:
        return f"""
        <script>
            alert('🚨 비밀번호 5회 오류로 계정이 잠겼습니다.\\n개발자에게 문의하여 잠금을 해제해주세요.');
            history.back();
        </script>
        """

    # DB 비밀번호 가져오기
    try:
        db_pw = user['password']
    except:
        db_pw = user[10]

    conn = sqlite3.connect('/home/huhihhuh/users.db')
    cursor = conn.cursor()

    # [보안 2] 검증
    if check_password_hash(db_pw, input_pw) or db_pw == input_pw:
        # ✅ 성공 -> 초기화
        cursor.execute("UPDATE users SET fail_count = 0 WHERE user_id = ?", (uid,))
        conn.commit()
        conn.close()

        # ✅ 인증 성공! 'edit_auth' 도장 발급 (register_page가 이거 검사함)
        session['edit_auth'] = uid

        # 3. edit_page 로 이동 (함수 이름 정확히!)
        return redirect(url_for('edit_page'))

    else:
        # ❌ 실패 -> 카운트 증가
        cursor.execute("UPDATE users SET fail_count = fail_count + 1 WHERE user_id = ?", (uid,))
        conn.commit()
        conn.close()
        return f"""
        <script>
            alert('비밀번호가 일치하지 않습니다! ❌\\n(현재 {fail_count + 1}회 오류 / 5회 시 잠김)');
            history.back();
        </script>
        """

# ------------------------------------------------------------------
# 5-2. 정보 수정 페이지 보여주기
@app.route('/edit_page')
def edit_page():
    # 1. 권한 검사 (edit_auth 도장이 있나?)
    uid = session.get('edit_auth')
    if not uid:
        return """<script>alert('접근 권한이 없습니다. 대시보드에서 비밀번호를 확인해주세요.'); location.href='/dashboard';</script>"""

    user = get_user_data(uid)
    if not user: return "회원 정보 없음"

    # 2. DB 데이터를 HTML에 넣기 좋게 가공 (pre_data)
    # user['birth_time']이 None이면 빈 문자열로 변환
    b_time = user['birth_time'] if user['birth_time'] else ""

    pre_data = {
        'name': user['name'],
        'phone': user['phone'],
        'birth_date': user['birth_date'],
        'birth_time': b_time,
        'gender': user['gender'],
        'calendar': user['calendar_type'],
        'noti_time': user['noti_time'],
        'is_early': (user['is_early'] == 1),     # 1이면 True (체크됨)
        'is_unknown': (not user['birth_time'])   # 시간이 없으면 모름(True)
    }

    return render_template('edit_info.html', data=pre_data)

# ------------------------------------------------------------------
# 5-3. 수정된 정보 DB에 저장하기 (UPDATE)
@app.route('/submit_edit', methods=['POST'])
def submit_edit():
    # 1. 권한 검사 (세션 체크)
    uid = session.get('edit_auth')
    if not uid:
        return "🚨 세션이 만료되었습니다. 다시 시도해주세요.", 403

    # 2. 폼 데이터 받기
    name = request.form.get('name')
    phone = request.form.get('phone')
    birth_date = request.form.get('birth_date')
    birth_time = request.form.get('birth_time')
    gender = request.form.get('gender')
    calendar_type = request.form.get('calendar_type')
    noti_time = request.form.get('noti_time')

    # 체크박스 처리
    is_early = 1 if request.form.get('is_early') else 0

    if request.form.get('unknown_time'):
        db_birth_time = None
    else:
        db_birth_time = birth_time

    # 3. 비밀번호 처리 (입력했을 때만 변경)
    password = request.form.get('password')

    conn = sqlite3.connect('/home/huhihhuh/users.db')
    cursor = conn.cursor()

    if password and password.strip():
        # [A] 비밀번호도 바꾸는 경우
        final_pw = generate_password_hash(password)
        cursor.execute("""
            UPDATE users
            SET name=?, phone=?, birth_date=?, birth_time=?, gender = ?, calendar_type=?, noti_time=?, is_early=?, password=?
            WHERE user_id=?
        """, (name, phone, birth_date, db_birth_time, gender, calendar_type, noti_time, is_early, final_pw, uid))
    else:
        # [B] 정보만 바꾸는 경우 (비밀번호 제외)
        cursor.execute("""
            UPDATE users
            SET name=?, phone=?, birth_date=?, birth_time=?, gender = ?, calendar_type=?, noti_time=?, is_early=?
            WHERE user_id=?
        """, (name, phone, birth_date, db_birth_time, gender, calendar_type, noti_time, is_early, uid))

    conn.commit()
    conn.close()

    # 4. 마무리 (권한 회수 후 대시보드로)
    session.pop('edit_auth', None)

    return """
    <script>
        alert('정보가 성공적으로 수정되었습니다! ✨');
        location.href = '/dashboard';
    </script>
    """






# ---------------------------------------------------------
# 6-1. 웹용 특정일 운세 처리
@app.route('/fortune_web', methods=['POST'])
def fortune_web():
    try :

        uid = session.get('dashboard_auth')

        if not uid:
            return jsonify({'error': '세션이 만료되었습니다. 다시 로그인해주세요.'})

        target_date = request.form.get('target_date').replace("-", "")

        user = get_user_data(uid)
        if not user:
            return jsonify({'error': '회원 정보를 찾을 수 없습니다.'})


        # 1. 권한 체크
        is_active, _ = check_subscription(user)
        if not is_active:
            return jsonify({"result": "🔒 프리미엄 권한이 필요합니다."})

        user_saju_list = get_user_saju_list(user)
        date_txt, luck_ganji_str = saju_logic.date_luck(target_date)
        analyzer = saju_logic.SajuAnalyzer(user_saju_list, list(luck_ganji_str))
        fortune_result = analyzer.sectioned_saju_output(date_txt)

        return jsonify({"result": fortune_result})

    except Exception as e:
        return jsonify({"result": f"분석 실패: {str(e)}"})

# ---------------------------------------------------------
# 6-2. 웹용 신년 운세 처리
@app.route('/new_year_page')
def new_year_page():

    uid = session.get('dashboard_auth')
    if not uid:
        return redirect('/login_page')

    user = get_user_data(uid)
    target_year = request.args.get('year', '2026') # 연도는 받아야 함

    # 1. 보안/권한 체크
    is_active, _ = check_subscription(user)
    if not is_active:
        return "🔒 프리미엄 권한이 필요합니다."

    # 2. 신년 운세 데이터 생성 (saju_logic 호출)
    # 총운
    user_saju_list = get_user_saju_list(user)
    date_txt, luck_ganji_str = saju_logic.date_luck(target_year)
    analyzer = saju_logic.SajuAnalyzer(user_saju_list, list(luck_ganji_str))
    year_luck_text = analyzer.sectioned_saju_output(date_txt)

    # 1월~12월 월별 운세 생성 (반복문)
    monthly_lucks = []
    for month in range(1, 13):
        # YYYYMM 형식 (예: 202601)
        date_str = f"{target_year}{month:02d}"
        date_txt, luck_ganji_str = saju_logic.date_luck(date_str)
        analyzer = saju_logic.SajuAnalyzer(user_saju_list, list(luck_ganji_str))
        luck = analyzer.sectioned_saju_output(date_txt)
        monthly_lucks.append({"month": month, "text": luck})

    # 3. 새 템플릿 렌더링
    return render_template('new_year_result.html',
                           user=user,
                           year=target_year,
                           total_luck=year_luck_text,
                           monthly_lucks=monthly_lucks)

# ---------------------------------------------------------
# 6-3. 궁합

# ---------------------------------------------------------
# 6-4. 대운






# ---------------------------------------------------------
# 7-1. FAQ 페이지
@app.route('/faq')
def faq_page():
    return render_template('faq.html')

# ---------------------------------------------------------
# 7-2. FAQ_block
@app.route('/faq_block', methods=['POST'])
def faq_block():

    req = request.get_json()
    uid = req['userRequest']['user']['id']

    my_domain = "https://huhihhuh.pythonanywhere.com"
    faq_url = f"{my_domain}/faq?"


    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "textCard": {
                        "text": "궁금한 점이 있으신가요?\n아래 버튼을 눌러 해석 원리와 용어 설명을 확인해보세요! 👇",
                        "buttons": [
                            {
                                "action": "webLink",
                                "label": "💡 자주 묻는 질문",
                                "webLinkUrl": faq_url
                            }
                        ]
                    }
                }
            ],
            "quickReplies": [
                { "messageText": "🏠 처음으로", "action": "message", "label": "🏠 처음으로" }
            ]
        }
    })






# 공통 운세 계산 로직
# -----------------------------------------------------------
# 1. 신규 유저용 가입 유도 카드 (풀 버전)
def get_register_card(uid, domain):
    eid = encrypt_id(uid)
    token = generate_security_token(eid)

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "basicCard": {
                        "title": "반가워요! 당신의 사주 파트너 오운비입니다 ☀️",
                        "description": "오운비는 AI와 명리학을 결합해 당신의 하루를 분석해요.\n정확한 분석을 위해 정보를 먼저 입력해주세요!",
                        "thumbnail": {
                            "imageUrl": "https://cdn.pixabay.com/photo/2016/11/29/05/45/astronomy-1867616_1280.jpg"
                        },
                        "buttons": [
                            {
                                "action": "webLink",
                                "label": "📝 정보 입력하기",
                                "webLinkUrl": f"{domain}/join_gate?eid={eid}&skey={token}"
                            },
                            {
                                "action": "message",
                                "label": "💬 오운비 서비스 소개",
                                "messageText": "채널 소개"
                            }
                        ]
                    }
                }
            ],
            "quickReplies": [
                { "action": "message", "label": "💡 자주 묻는 질문", "messageText": "💡 자주 묻는 질문" }
            ]
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)