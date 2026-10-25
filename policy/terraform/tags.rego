package terraform.tags

import rego.v1

required_tags := {"Project", "Owner", "Environment"}

deny contains msg if {
	some rc in input.resource_changes
	not "delete" in rc.change.actions
	rc.change.after != null
	tags := object.get(rc.change.after, "tags_all", null)
	tags != null
	present := {k | _ = tags[k]}
	missing := required_tags - present
	count(missing) > 0
	msg := sprintf("%s: missing required tags: %v", [rc.address, sort(missing)])
}