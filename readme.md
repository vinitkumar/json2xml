## About

[![Build Status](https://travis-ci.org/vinitkumar/json2xml.svg?branch=master)](https://travis-ci.org/vinitkumar/json2xml)
[![Downloads](https://pepy.tech/badge/json2xml)](https://pepy.tech/project/json2xml)

A simple python utility to convert JSON to XML(supports latest stable version of 3.7.x, 3.6.x and 3.5.x series).
It accepts string from url, file, and directly from json string

### Installation

```
pip3 install json2xml
```

### Usage


```python
# from file system
from src.json2xml import Json2xml
data = Json2xml.fromjsonfile('examples/example.json').data
data_object = Json2xml(data)
data_object.json2xml() #xml output

# From an URL
from src.json2xml import Json2xml
data = Json2xml.fromurl('https://coderwall.com/vinitcool76.json').data
data_object = Json2xml(data)
data_object.json2xml() #xml output

# From JSON string
from src.json2xml import Json2xml
data = Json2xml.fromstring('{"login":"mojombo","id":1,"avatar_url":"https://avatars0.githubusercontent.com/u/1?v=4"}').data
data_object = Json2xml(data)
data_object.json2xml() #xml output
```

#### Custom wrapper and indent size

A custom wrapper other than `all` and default indent size of `2` can also be passed

Eg:

```python
# from file system
from src.json2xml import Json2xml
data = Json2xml.fromjsonfile('examples/example.json').data
data_object = Json2xml(data, wrapper="custom", indent=4)
data_object.json2xml() #xml output
```

will output this:


```xml
<custom>
    <avatar_url>https://github.com/images/error/octocat_happy.gif</avatar_url>
    <bio>There once was...</bio>
    <blog>https://github.com/blog</blog>
    <company>GitHub</company>
    <created_at>2008-01-14T04:33:35Z</created_at>
    <email>octocat@github.com</email>
    <events_url>https://api.github.com/users/octocat/events{/privacy}</events_url>
    <followers>20</followers>
    <followers_url>https://api.github.com/users/octocat/followers</followers_url>
    <following>0</following>
    <following_url>https://api.github.com/users/octocat/following{/other_user}</following_url>
    <gists_url>https://api.github.com/users/octocat/gists{/gist_id}</gists_url>
    <gravatar_id></gravatar_id>
    <hireable>False</hireable>
    <html_url>https://github.com/octocat</html_url>
    <id>1</id>
    <location>San Francisco</location>
    <login>octocat</login>
    <name>monalisa octocat</name>
    <organizations_url>https://api.github.com/users/octocat/orgs</organizations_url>
    <public_gists>1</public_gists>
    <public_repos>2</public_repos>
    <received_events_url>https://api.github.com/users/octocat/received_events</received_events_url>
    <repos_url>https://api.github.com/users/octocat/repos</repos_url>
    <site_admin>False</site_admin>
    <starred_url>https://api.github.com/users/octocat/starred{/owner}{/repo}</starred_url>
    <subscriptions_url>https://api.github.com/users/octocat/subscriptions</subscriptions_url>
    <type>User</type>
    <updated_at>2008-01-14T04:33:35Z</updated_at>
    <url>https://api.github.com/users/octocat</url>
</custom>
```


### Bugs, features

- If you find any bug, create an [issue for bug](https://github.com/vinitkumar/json2xml/issues/new?assignees=&labels=&template=bug_report.md&title=)
- If you want a feature to be supported, open an [issue for feature](https://github.com/vinitkumar/json2xml/issues/new?assignees=&labels=&template=feature_request.md&title=)
