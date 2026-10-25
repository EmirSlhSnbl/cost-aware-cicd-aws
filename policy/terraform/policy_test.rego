package terraform.policy_test

import rego.v1

full_tags := {"Project": "p", "Owner": "o", "Environment": "dev", "ManagedBy": "terraform"}

test_missing_owner_is_denied if {
	plan := {"resource_changes": [{
		"address": "aws_vpc.x",
		"type": "aws_vpc",
		"change": {"actions": ["create"], "after": {"tags_all": {"Project": "p", "Environment": "dev"}}},
	}]}
	count(data.terraform.tags.deny) == 1 with input as plan
}

test_full_tags_pass if {
	plan := {"resource_changes": [{
		"address": "aws_vpc.x",
		"type": "aws_vpc",
		"change": {"actions": ["create"], "after": {"tags_all": full_tags}},
	}]}
	count(data.terraform.tags.deny) == 0 with input as plan
}

test_deleted_resource_ignored if {
	plan := {"resource_changes": [{
		"address": "aws_vpc.x",
		"type": "aws_vpc",
		"change": {"actions": ["delete"], "after": null},
	}]}
	count(data.terraform.tags.deny) == 0 with input as plan
}

test_alb_is_forbidden if {
	plan := {"resource_changes": [{
		"address": "aws_lb.demo",
		"type": "aws_lb",
		"change": {"actions": ["create"], "after": {"tags_all": full_tags}},
	}]}
	count(data.terraform.forbidden.deny) == 1 with input as plan
}

test_destroying_alb_is_allowed if {
	plan := {"resource_changes": [{
		"address": "aws_lb.demo",
		"type": "aws_lb",
		"change": {"actions": ["delete"], "after": null},
	}]}
	count(data.terraform.forbidden.deny) == 0 with input as plan
}

test_large_task_warns if {
	plan := {"resource_changes": [{
		"address": "module.ecs.aws_ecs_task_definition.app",
		"type": "aws_ecs_task_definition",
		"change": {"actions": ["create"], "after": {"cpu": "1024", "memory": "4096"}},
	}]}
	count(data.terraform.sizing.warn) == 2 with input as plan
}

test_default_task_does_not_warn if {
	plan := {"resource_changes": [{
		"address": "module.ecs.aws_ecs_task_definition.app",
		"type": "aws_ecs_task_definition",
		"change": {"actions": ["create"], "after": {"cpu": "256", "memory": "512"}},
	}]}
	count(data.terraform.sizing.warn) == 0 with input as plan
}

test_many_tasks_warns if {
	plan := {"resource_changes": [{
		"address": "module.ecs.aws_ecs_service.app",
		"type": "aws_ecs_service",
		"change": {"actions": ["create"], "after": {"desired_count": 5}},
	}]}
	count(data.terraform.sizing.warn) == 1 with input as plan
}