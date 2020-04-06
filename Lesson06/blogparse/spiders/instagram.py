# -*- coding: utf-8 -*-
import scrapy
import re
import json
from urllib.parse import urljoin, urlencode
from copy import deepcopy


class InstagramSpider(scrapy.Spider):
    name = 'instagram'
    allowed_domains = ['instagram.com']
    start_urls = ['https://www.instagram.com/']
    parse_users = ['realdonaldtrump', 'damedvedev', ]
    variables = {
        'id': '',
        'include_reel': True,
        'fetch_mutual': False,
        'first': 100,
    }
    graphql_url = 'https://www.instagram.com/graphql/query/?'

    def __init__(self, logpass: tuple, **kwargs):
        self.login, self.pswd = logpass
        self.followed_query_hash = 'c76146de99bb02f6415203be841dd25a'
        self.following_query_hash = 'd04b0a864b4b54837c0d870b0e77e076'
        super().__init__(**kwargs)

    def parse(self, response):
        login_url = 'https://www.instagram.com/accounts/login/ajax'
        csrf_token = self.fetch_csrf_token(response.text)
        yield scrapy.FormRequest(
            login_url,
            method='POST',
            callback=self.main_parse,
            formdata={
                'username': self.login,
                'password': self.pswd,
            },
            headers={
                'X-CSRFToken': csrf_token
            }
        )

    def main_parse(self, response):
        j_resp = json.loads(response.text)
        if j_resp.get('authenticated'):
            for u_name in self.parse_users:
                yield response.follow(urljoin(self.start_urls[0], u_name), callback=self.parse_user, cb_kwargs={'user_name': u_name})

    def parse_user(self, response, user_name):
        user_id = self.fetch_user_id(response.text, user_name=user_name)
        user_vars = deepcopy(self.variables)
        user_vars.update({'id': user_id})
        followed_url = self.make_followed_graphql_url(user_vars)
        following_url = self.make_following_graphql_url(user_vars)
        yield response.follow(
            followed_url,
            callback=self.parse_followers,
            cb_kwargs={
                'user_vars': user_vars,
                'user_name': user_name
            })
        yield response.follow(
            following_url,
            callback=self.parse_following,
            cb_kwargs={
                'user_vars': user_vars,
                'user_name': user_name
            })

    def parse_followers(self, response, user_vars, user_name):
        j_response = json.loads(response.text)
        if j_response.get('data').get('user').get('edge_followed_by').get('page_info').get('has_next_page'):
            user_vars.update({
                'after': j_response.get('data').get('user').get('edge_followed_by').get('page_info').get('end_cursor')
            })
            url = self.make_followed_graphql_url(user_vars)
            yield response.follow(
                url,
                callback=self.parse_followers,
                cb_kwargs={
                    'user_vars': user_vars,
                    'user_name': user_name
                }
            )
            followers = j_response.get('data').get('user').get('edge_followed_by').get('edges')
            for follower in followers:
                yield {
                    'user_name': user_name,
                    'user_id': user_vars['id'],
                    'follower': follower.get('node')
                }

    def parse_following(self, response, user_vars, user_name):
        j_response = json.loads(response.text)
        if j_response.get('data').get('user').get('edge_follow').get('page_info').get('has_next_page'):
            user_vars.update({
                'after': j_response.get('data').get('user').get('edge_follow').get('page_info').get('end_cursor')
            })
            url = self.make_following_graphql_url(user_vars)
            yield response.follow(
                url,
                callback=self.parse_following,
                cb_kwargs={
                    'user_vars': user_vars,
                    'user_name': user_name
                }
            )
            followings = j_response.get('data').get('user').get('edge_follow').get('edges')
            for following in followings:
                yield {
                    'user_name': user_name,
                    'user_id': user_vars['id'],
                    'following': following.get('node')
                }

    def fetch_csrf_token(self, text):
        matched = re.search('\"csrf_token\":\"\\w+\"', text).group()
        return matched.split(':').pop().replace(r'"', '')

    def fetch_user_id(self, text, user_name):
        matched = re.search(f'{{\"id\":\"\\d+\",\"username\":\"{user_name}\"}}', text).group()
        return json.loads(matched).get('id')

    def make_followed_graphql_url(self, user_vars):
        return f'{self.graphql_url}query_hash={self.followed_query_hash}&{urlencode(user_vars)}'

    def make_following_graphql_url(self, user_vars):
        return f'{self.graphql_url}query_hash={self.following_query_hash}&{urlencode(user_vars)}'
