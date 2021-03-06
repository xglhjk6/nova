# Copyright 2012 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import base64

from webob import exc

from nova import compute
from nova import exception
from nova import policy
from nova.i18n import _
from nova.api.openstack import wsgi
from nova.api.openstack import extensions


authorize = extensions.extension_authorizer('compute', 'eayun-userdata')


class EayunUserDataController(wsgi.Controller):
    """EayunStack userdata controller."""
    def __init__(self, ext_mgr=None):
        super(EayunUserDataController, self).__init__()
        self.compute_api = compute.API()
        self.ext_mgr = ext_mgr

    def _validate_user_data(self, user_data):
        """Check if the user_data is encoded properly."""
        if not user_data:
            return
        try:
            base64.b64decode(user_data)
        except:
            expl = _('Userdata content cannot be decoded')
            raise exc.HTTPBadRequest(explanation=expl)

    def _get_userdata(self, instance):
        user_data = {'user_data': instance.get("user_data", None)}

        return user_data

    def _is_valid_body(self, body, entity_name):
        if not (body and entity_name in body):
            return False

        def is_dict(d):
            return type(d) is dict

        return is_dict(body)

    def show(self, req, id):
        """Return userdata by server id."""
        context = req.environ['nova.context']
        authorize(context)

        try:
            instance = self.compute_api.get(context, id,
                                            want_objects=True)
            req.cache_db_instance(instance)
        except exception.NotFound:
            msg = _("Instance could not be found")
            raise exc.HTTPNotFound(explanation=msg)

        return self._get_userdata(instance)

    def update(self, req, id, body):
        """Update userdata by server id."""
        if not self._is_valid_body(body, 'user_data'):
            raise exc.HTTPUnprocessableEntity()

        context = req.environ['nova.context']
        authorize(context)
        update_dict = {}

        user_data = body['user_data']
        self._validate_user_data(user_data)
        update_dict['user_data'] = user_data

        try:
            instance = self.compute_api.get(context, id,
                                            want_objects=True)
        except exception.NotFound:
            msg = _("Instance could not be found")
            raise exc.HTTPNotFound(explanation=msg)

        req.cache_db_instance(instance)
        policy.enforce(context, 'compute_extension:eayun-userdata:update',
                       instance)
        instance.update(update_dict)
        instance.save()

        return self._get_userdata(instance)


class Eayun_user_data(extensions.ExtensionDescriptor):
    """Add userdata extension for v2 API."""

    name = "EayunUserData"
    alias = "eayun-userdata"
    namespace = ("www.eayun.cn")
    updated = "2017-01-10T00:00:00Z"

    def get_resources(self):
        resources = []
        res = extensions.ResourceExtension('eayun-userdata',
                                           EayunUserDataController(
                                               self.ext_mgr))
        resources.append(res)
        return resources
