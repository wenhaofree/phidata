import schedule
import time
import app_local
from datetime import datetime, timedelta

def job():
    # 体育单独的发布
    try:
        print('[新闻格式化开始发布头条数据:程序运行时间: %s]' % time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
        app_local.main_pro()
    except Exception as e:
        print(f'格式化异常:{e}')
    
    print('[格式化文章发布完毕,定时程序结束...]')

def schedule_job():
    schedule.every(5).minutes.do(job)
    # schedule.every(10).seconds.do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    print('[程序启动...格式化文章]')
    schedule_job()
