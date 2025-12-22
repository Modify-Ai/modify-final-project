# reset_db.py
import sqlalchemy
from sqlalchemy import create_engine, text

# 1. RDS 주소 (alembic.ini에 넣었던 것과 동일)
DATABASE_URL = "postgresql://modify_user:modify_password@modify-db.cdu4sc0aoj43.ap-northeast-2.rds.amazonaws.com/modify_db"

# 2. 엔진 생성
engine = create_engine(DATABASE_URL)

def reset_database():
    print("🚀 DB 초기화를 시작합니다...")
    with engine.connect() as connection:
        # 트랜잭션 시작
        trans = connection.begin()
        try:
            # 3. 모든 테이블 강제 삭제 (Cascade)
            # alembic_version 테이블이 여기서 삭제되면 에러가 해결됩니다.
            print("Running: DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
            connection.execute(text("DROP SCHEMA public CASCADE;"))
            connection.execute(text("CREATE SCHEMA public;"))
            connection.execute(text("GRANT ALL ON SCHEMA public TO modify_user;"))
            connection.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            
            trans.commit()
            print("✅ DB 초기화 완료! 이제 깨끗합니다.")
        except Exception as e:
            trans.rollback()
            print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    reset_database()