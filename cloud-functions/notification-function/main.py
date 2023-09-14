import functions_framework

@functions_framework.http
def handle(request):
    # This function should parse in the request and send it as
    # a message to the Slack channel.
    return request
