#     Copyright 2014 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
"""
.. module: security_monkey.watchers.iam.iam_user
    :platform: Unix

.. version:: $$VERSION$$
.. moduleauthor:: Patrick Kelley <pkelley@netflix.com> @monkeysecurity

"""
from cloudaux.orchestration.aws.iam.user import get_user
from cloudaux.aws.iam import list_users
from security_monkey.decorators import record_exception, iter_account_region
from security_monkey.watcher import ChangeItem
from security_monkey.watcher import Watcher
from security_monkey import app


class IAMUser(Watcher):
    index = 'iamuser'
    i_am_singular = 'IAM User'
    i_am_plural = 'IAM Users'

    def __init__(self, accounts=None, debug=False):
        super(IAMUser, self).__init__(accounts=accounts, debug=debug)

    @record_exception(source="iamuser-watcher", pop_exception_fields=True)
    def list_users(self, **kwargs):
        users = list_users(**kwargs)
        return [user for user in users if not self.check_ignore_list(user['UserName'])]

    @record_exception(source="iamuser-watcher", pop_exception_fields=True)
    def process_user(self, user, **kwargs):
        app.logger.debug("Slurping {index} ({name}) from {account}".format(
            index=self.i_am_singular,
            name=user['UserName'],
            account=kwargs['account_number']))
        return get_user(user, **kwargs)

    def slurp(self):
        self.prep_for_slurp()

        @iter_account_region(index=self.index, accounts=self.accounts, exception_record_region='universal')
        def slurp_items(**kwargs):
            item_list = []
            users = self.list_users(**kwargs)

            for user in users:
                user = self.process_user(user, name=user['UserName'], **kwargs)
                if user:
                    item = IAMUserItem.from_slurp(user, **kwargs)
                    item_list.append(item)

            return item_list, kwargs.get('exception_map', {})
        return slurp_items()


class IAMUserItem(ChangeItem):
    def __init__(self, account=None, name=None, arn=None, config={}):
        super(IAMUserItem, self).__init__(
            index=IAMUser.index,
            region='universal',
            account=account,
            name=name,
            arn=arn,
            new_config=config)

    @classmethod
    def from_slurp(cls, user, **kwargs):
        return cls(
            account=kwargs['account_name'],
            name=user['UserName'],
            config=user,
            arn=user['Arn'])
