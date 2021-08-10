from time import sleep
import pyautogui

# https://neerc.ifmo.ru/school/io/archive/20190324/archive-20190324-large.zip demo orders
# http://neerc.ifmo.ru/school/io/archive/20210227/archive-20210227-large.zip only add-on-array

keys = ["down", "down", "down", "down", "down", "enter"]


def slow_press(keys, interval):
    for key in keys:
        pyautogui.press(key, interval=interval)


def status_demo():
    pyautogui.write('polygon-uploader status\n', interval=0.15)
    sleep(1)
    slow_press(keys, 0.15)
    sleep(0.3)


def scoring_demo():
    pyautogui.write("polygon-uploader scoring\n", interval=0.15)
    sleep(1)
    slow_press(keys, 0.15)
    sleep(0.3)
    slow_press(["y"], 0.15)
    sleep(3)
    slow_press(["y"], 0.15)
    sleep(0.3)


def upload_demo():
    pyautogui.write("polygon-uploader upload\n", interval=0.15)
    sleep(1)
    slow_press(keys, 0.15)
    id = 178223
    pyautogui.write(str(id) + "\n", interval=0.15)
    sleep(1)
    slow_press(["y"], 0.15)


sleep(1)

status_demo()
scoring_demo()
upload_demo()
