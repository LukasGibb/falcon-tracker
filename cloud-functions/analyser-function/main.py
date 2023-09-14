import functions_framework

@functions_framework.http
def handle(request):
    # This funcrion should compare a current and previous annotation
    # If condition is met it should push a message to the notifier topic
    return request
