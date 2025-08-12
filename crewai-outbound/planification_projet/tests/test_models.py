from src.models.plan import ProjectPlan, TaskEstimate, Milestone

def test_models_ok():
    plan = ProjectPlan(
        tasks=[TaskEstimate(task_name="Test", estimated_time_hours=1.0, required_resources=["X"])],
        milestones=[Milestone(milestone_name="M1", tasks=["Test"])]
    )
    assert plan.tasks[0].task_name == "Test"
