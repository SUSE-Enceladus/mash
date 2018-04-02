# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#


job_message = {
    "type": "object",
    "properties": {
        "provider": {"enum": ["azure", "ec2"]},
        "provider_accounts": {
            "type": "array",
            "items": {"type": "string"},
            "uniqueItems": True
        },
        "requesting_user": {"type": "string"},
        "last_service": {
            "enum": [
                'obs', 'uploader', 'testing', 'replication',
                'publisher', 'deprecation', 'pint'
            ]
        },
        "utctime": {
            "anyOf": [
                {"enum": ["always", "now"]},
                {"type": "string", "format": "date-time"}
            ]
        },
        "image": {"type": "string"},
        "cloud_image_name": {"type": "string"},
        "old_cloud_image_name": {"type": "string"},
        "project": {"type": "string"},
        "conditions": {
            "type": "array",
            "items": {
                "anyOf": [
                    {"$ref": "#definitions/image_conditions"},
                    {"$ref": "#definitions/package_conditions"}
                ]
            }
        },
        "share_with": {
            "anyOf": [
                {"enum": ["all", "none"]},
                {
                    "type": "string",
                    "format": "regex",
                    "pattern": "^[0-9]{12}(,[0-9]{12})*$"
                }
            ]
        },
        "allow_copy": {"type": "boolean"},
        "image_description": {"type": "string"},
        "target_regions": {
            "type": "object",
            "properties": {
                "accounts": {
                    "type": "array",
                    "items": {"$ref": "#definitions/account"}
                },
                "groups": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True
                }
            }
        },
        "tests": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "additionalProperties": False,
    "definitions": {
        "image_conditions": {
            "properties": {
                "image": {"type": "string"}
            },
            "additionalProperties": False
        },
        "package_conditions": {
            "properties": {
                "package": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "additionalProperties": False
        },
        "account": {
            "properties": {
                "name": {"type": "string"},
                "regions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "uniqueItems": True
                }
            },
            "additionalProperties": False
        }
    }
}
