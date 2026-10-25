package terraform.forbidden

import rego.v1

# Sabit aylik maliyet getiren, projenin kapsami disinda kalan kaynak tipleri.
forbidden_types := {
	"aws_nat_gateway",
	"aws_lb",
	"aws_alb",
	"aws_db_instance",
	"aws_rds_cluster",
	"aws_eks_cluster",
	"aws_elasticache_cluster",
	"aws_redshift_cluster",
}

deny contains msg if {
	some rc in input.resource_changes
	rc.type in forbidden_types
	some action in rc.change.actions
	action in {"create", "update"}
	msg := sprintf("%s: resource type %s is forbidden by the cost guardrails", [rc.address, rc.type])
}