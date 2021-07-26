import sched
from datetime import datetime
import time
import threading
def addition(a,b):
    print("\nInside Addition : ", datetime.now())
    print("Time : ", time.monotonic())
    print("Result : ", a+b)

s = sched.scheduler()

print("Start Time : ", datetime.now(), "\n")

current_time = time.monotonic()
five_seconds_past_curr_time = current_time + 5

event1 = s.enterabs(five_seconds_past_curr_time, 1, addition, kwargs = {"a":10, "b":20})

print("Current Time  : ", current_time)
print("\nEvent Created : ", event1)

t = threading.Thread(target=s.run)
t.start()

print("\nEnd   Time : ", datetime.now())