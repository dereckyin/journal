"""Seed sample data. Usage: `flask --app run.py seed` or `python -m app.seed`."""

from datetime import datetime, timedelta

from . import create_app
from .extensions import db
from .models import (
    Department,
    PersonalCategory,
    Project,
    ProjectMember,
    TimeEntry,
    User,
)


def seed() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()

        if User.query.filter_by(username="admin").first():
            print("Seed data already present; skipping.")
            return

        # Departments (we'll attach managers later)
        engineering = Department(name="工程部")
        design = Department(name="設計部")
        db.session.add_all([engineering, design])
        db.session.flush()

        # Users
        admin = User(
            username="admin",
            full_name="系統管理員",
            email="admin@example.com",
            role=User.ROLE_ADMIN,
            hourly_rate=0,
        )
        admin.set_password("admin123")

        manager1 = User(
            username="manager1",
            full_name="王主管",
            email="manager1@example.com",
            role=User.ROLE_MANAGER,
            department_id=engineering.id,
            hourly_rate=1200,
        )
        manager1.set_password("manager123")

        emp1 = User(
            username="emp1",
            full_name="陳小明",
            email="emp1@example.com",
            role=User.ROLE_EMPLOYEE,
            department_id=engineering.id,
            hourly_rate=600,
        )
        emp1.set_password("emp123")

        emp2 = User(
            username="emp2",
            full_name="林小華",
            email="emp2@example.com",
            role=User.ROLE_EMPLOYEE,
            department_id=engineering.id,
            hourly_rate=550,
        )
        emp2.set_password("emp123")

        emp3 = User(
            username="emp3",
            full_name="黃設計",
            email="emp3@example.com",
            role=User.ROLE_EMPLOYEE,
            department_id=design.id,
            hourly_rate=700,
        )
        emp3.set_password("emp123")

        db.session.add_all([admin, manager1, emp1, emp2, emp3])
        db.session.flush()

        engineering.manager_id = manager1.id

        # Projects
        proj_a = Project(
            code="PA-001",
            name="客戶 A 官網改版",
            description="RWD 改版與 CMS 串接",
            budget=500000,
            color="#409EFF",
            created_by=admin.id,
        )
        proj_b = Project(
            code="PB-002",
            name="內部 ERP 系統",
            description="採購與庫存模組",
            budget=800000,
            color="#67C23A",
            created_by=admin.id,
        )
        db.session.add_all([proj_a, proj_b])
        db.session.flush()

        db.session.add_all(
            [
                ProjectMember(project_id=proj_a.id, user_id=emp1.id),
                ProjectMember(project_id=proj_a.id, user_id=emp3.id),
                ProjectMember(project_id=proj_a.id, user_id=manager1.id),
                ProjectMember(project_id=proj_b.id, user_id=emp1.id),
                ProjectMember(project_id=proj_b.id, user_id=emp2.id),
                ProjectMember(project_id=proj_b.id, user_id=manager1.id),
            ]
        )

        # Personal categories
        cat_meeting = PersonalCategory(name="內部會議", color="#E6A23C")
        cat_training = PersonalCategory(name="教育訓練", color="#909399")
        cat_admin = PersonalCategory(name="行政事務", color="#F56C6C")
        db.session.add_all([cat_meeting, cat_training, cat_admin])
        db.session.flush()

        # Sample entries: this week, Mon 09-12 for emp1 on proj_a
        today = datetime.utcnow().date()
        monday = today - timedelta(days=today.weekday())
        base = datetime.combine(monday, datetime.min.time())

        db.session.add_all(
            [
                TimeEntry(
                    user_id=emp1.id,
                    project_id=proj_a.id,
                    title="首頁切版",
                    description="完成 hero section 與導覽列",
                    start_time=base + timedelta(hours=9),
                    end_time=base + timedelta(hours=12),
                ),
                TimeEntry(
                    user_id=emp1.id,
                    category_id=cat_meeting.id,
                    title="專案週會",
                    start_time=base + timedelta(hours=13),
                    end_time=base + timedelta(hours=14),
                ),
                TimeEntry(
                    user_id=emp1.id,
                    project_id=proj_b.id,
                    title="ERP API 設計",
                    start_time=base + timedelta(hours=14),
                    end_time=base + timedelta(hours=18),
                ),
                TimeEntry(
                    user_id=emp2.id,
                    project_id=proj_b.id,
                    title="採購模組需求訪談",
                    start_time=base + timedelta(days=1, hours=9),
                    end_time=base + timedelta(days=1, hours=12),
                ),
                TimeEntry(
                    user_id=emp3.id,
                    project_id=proj_a.id,
                    title="視覺提案",
                    start_time=base + timedelta(days=2, hours=10),
                    end_time=base + timedelta(days=2, hours=16),
                ),
            ]
        )

        db.session.commit()
        print("Seeded. Accounts:")
        print("  admin / admin123      (管理者)")
        print("  manager1 / manager123 (工程部主管)")
        print("  emp1,emp2,emp3 / emp123")


if __name__ == "__main__":
    seed()
