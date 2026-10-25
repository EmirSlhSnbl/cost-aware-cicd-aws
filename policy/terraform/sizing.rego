package terraform.sizing

import rego.v1

max_fargate_cpu := 512

max_fargate_memory := 1024

max_desired_count := 2

warn contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_ecs_task_definition"
	rc.change.after != null
	to_number(rc.change.after.cpu) > max_fargate_cpu
	msg := sprintf("%s: Fargate cpu %v is above the recommended maximum of %d", [rc.address, rc.change.after.cpu, max_fargate_cpu])
}

warn contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_ecs_task_definition"
	rc.change.after != null
	to_number(rc.change.after.memory) > max_fargate_memory
	msg := sprintf("%s: Fargate memory %v is above the recommended maximum of %d", [rc.address, rc.change.after.memory, max_fargate_memory])
}

warn contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_ecs_service"
	rc.change.after != null
	rc.change.after.desired_count > max_desired_count
	msg := sprintf("%s: desired_count %d is above the recommended maximum of %d", [rc.address, rc.change.after.desired_count, max_desired_count])
}