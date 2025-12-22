import sqlalchemy
from sqlalchemy import create_engine, text

# RDS 주소
db_url = 'postgresql://modify_user:modify_password@modify-db.cdu4sc0aoj43.ap-northeast-2.rds.amazonaws.com/modify_db'
engine = create_engine(db_url)

with engine.connect() as conn:
    # 이메일 확인: admin@modify.com
    email = 'admin@modify.com' 
    
    # 1. 슈퍼유저로 승격 쿼리 실행
    # (f-string 문법을 파이썬에 맞게 수정함)
    conn.execute(text(f"UPDATE users SET is_superuser = true WHERE email = '{email}'"))
    conn.commit()
    
    print(f"✅ {email} 계정이 관리자(Superuser)로 변경되었습니다. 이제 로그아웃 후 다시 로그인하세요!")