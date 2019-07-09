[![PyPi](https://img.shields.io/pypi/v/storyscript.svg?maxAge=600&style=for-the-badge)](https://pypi.python.org/pypi/storyscript)
[![CircleCI](https://img.shields.io/circleci/project/github/storyscript/storyscript/master.svg?style=for-the-badge)](https://circleci.com/gh/storyscript/storyscript)
[![Codecov](https://img.shields.io/codecov/c/github/storyscript/storyscript.svg?style=for-the-badge)](https://codecov.io/github/storyscript/storyscript)
[![Docs](https://img.shields.io/badge/docs-online-brightgreen.svg?style=for-the-badge)](https://docs.storyscript.io)
[![Devdocs](https://img.shields.io/badge/devdocs-online-brightgreen.svg?style=for-the-badge)](https://storyscript.readthedocs.io)


<div align="center">
<img src="https://user-images.githubusercontent.com/4370550/56803568-460e5800-6823-11e9-8a70-25ab4b7e32ea.png" width="275">
</div>

## &#x1F44B; Meet Storyscript
The [DSL](https://en.wikipedia.org/wiki/Domain-specific_language) for **Application Storytelling**.
Develop rapidly, deploy natively to the cloud and focus on what matters most: business-logic.
Designed with :heart: by [Storyscript](https://storyscript.io) on a mission to bring application development to the next level.

```coffee
# Applications are stories of data.
when http server listen path: '/' as request     # Serverless
    result = anyMicroservice action key: value   # Written in any language wrapped in Docker or RKT
    result = anyFunction(key: value)             # Lambda, OpenFaaS, KNative or Storyscript
    items = 'string' split by: ','               # Mutations == No middleware
    data = OpenAPI get users: users              # OpenAPI & AsyncAPI for legacy system support
    sent = machinebox/textbox process input:data # Free/Paid Serivces
    if sent.positive                             # Conditions
        foreach list as item                     # Turing complete
            # ...
    request write content: 'Hello World!'

# Next launch on the Storyscript Platform
$ story deploy  # Zero-devop deployments into Kubernetes
```

&#x1F4AF;Open Source for a delicious application development. :sparkles::cake::sparkles:

> &#x1F680;Choose: hosted **Storyscript Cloud** or `helm install story` for on-premises deployments.

## Installation

Storyscript can be installed with [pip](https://pip.pypa.io):

```sh
pip install storyscript
```

## Usage

Write a simple story:

```sh
echo "alpine echo text:'hello world!'" > hello.story
```

Compile a story to JSON:

```sh
storyscript compile -j hello.story
```

## Editor plugins

- [VSCode](https://asyncy.click/vscode)
- [Atom](https://github.com/storyscript/atom)

## Development documentation

[Development docs](https://storyscript.readthedocs.io) are provided for those
who wish to contribute to the project or want to understand how to execute
compiled stories.

## Contributing

If you want to contribute to Storyscript, you can join the community at
[our slack](https://asyncy.click/slack) where we discuss features and future
plans.

You can find open issues on [github](https://github.com/storyscript/storyscript/issues),
along with [contribution guidelines](https://github.com/storyscript/storyscript/blob/master/CONTRIBUTING.md)
for happy coding.
There are [simple issues](https://github.com/storyscript/storyscript/issues?q=is%3Aopen+is%3Aissue+label%3A%22good+first+issue%22)
for new contributors and
[issues that need help](https://github.com/storyscript/storyscript/issues?q=is%3Aopen+is%3Aissue+label%3A%22help+wanted%22)

### Contributors

The list of contributors is available [here](https://github.com/storyscript/storyscript/contributors)

## Issues

* For problems directly related to the CLI: [Add an issue on GitHub.](https://github.com/storyscript/cli/issues/new)
* To share feedback and suggestions: [We appreciate your ideas and honesty!](https://asyncy.click/feedback)
* For other issues: [Submit a support ticket.](mailto:support@storyscript.io)