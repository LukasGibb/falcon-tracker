import functions_framework

@functions_framework.http
def handle(request):
    # This function should parse in the request and send it as
    # a message to the Slack channel.
    print("Notification function called...")
    print(request.get_json())
    return 'ok', 200
