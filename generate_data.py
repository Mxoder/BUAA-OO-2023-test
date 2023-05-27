import random
import string
from collections import deque
from datetime import datetime, timedelta

_data_file = ''
_ans_file = ''
_res_file = ''
_res_store = True

books = {}
unshelved = {}
students = {}
max_date_limit = True
cur_date = datetime(2023, 1, 1).date()
last_arranged_date = datetime(2023, 1, 1).date()
waiting_list = deque()
today_orders_count = {}  # <stu_id, orders_count>
data_list = []
ans_list = []
res_list = []


def generate_books(account):
    # 策略：生成 {type}-{四位随机数} 作为书号，保证不重复，副本数为 1~10
    global books
    data_list.append(str(account))
    while len(books) < account:
        book_type = random.choice(["A", "B", "C"])
        book_serial_no = str(random.randint(0, 9999)).zfill(4)
        book_num = f'{book_type}-{book_serial_no}'
        if book_num not in books:
            copies = random.randint(1, 10)
            books[book_num] = copies
            line = ''.join('{0} {1}'.format(book_num, copies))
            data_list.append(line)


def generate_students(account):
    # 策略：生成 8 位随机 ascii 码作为学号，每位同学借到的书采用 set 存储（不重复）
    global students
    ascii_chars = string.ascii_letters + string.digits + string.punctuation
    while len(students) < account:
        student_id = ''.join(random.choices(ascii_chars, k=8))
        if student_id not in students:
            borrowed_B = set()
            borrowed_C = set()
            students[student_id] = {'B': borrowed_B, 'C': borrowed_C}


def generate_date(delta=-1):
    # 策略：按照 6:3:1 的几率生成 0:(1~3):(4~8) 的时间差
    global cur_date, max_date_limit, today_orders_count
    rand_seed = random.random()
    if delta <= 0:
        if rand_seed < 0.6:
            days_between = 0
        elif rand_seed < 0.9:
            days_between = random.randint(1, 3)
        else:
            days_between = random.randint(4, 8)
    else:
        days_between = int(delta)
    cur_date += timedelta(days=days_between)
    today_orders_count = {}  # empty the counter
    if max_date_limit and cur_date >= datetime(2023, 12, 31).date():
        cur_date = datetime(2023, 12, 31).date()
    return cur_date


def try_to_borrow():
    # 要求：必须是【图书馆初始拥有的书】
    # 策略：0.4 的几率请求借已有的书，0.6 的几率请求借图书馆出现过的书（也可能已经借过）
    global students, books
    date = generate_date()
    rand_seed = random.random()
    if rand_seed < 0.4:
        stu = get_student_with_books()
        if stu is None:
            return
        else:
            if len(students[stu]['B']) <= 0:
                book = random.sample(students[stu]['C'], 1)[0]
            elif len(students[stu]['C']) <= 0:
                book = random.sample(students[stu]['B'], 1)[0]
            else:
                # 如果有 B 书，80% 几率借 B 书
                rand_seed = random.random()
                if rand_seed < 0.8:
                    book = random.sample(students[stu]['B'], 1)[0]
                else:
                    book = random.sample(students[stu]['C'], 1)[0]
    else:
        stu = random.choice(list(students.keys()))
        book = random.choice(list(books.keys()))
    # 在最开始，先处理堆积的预约
    handle_arrange()
    # 再加入新指令
    line = ''.join(f'[{date}] {stu} borrowed {book}')
    data_list.append(line)
    handle_borrow(stu, book)


def try_to_return():
    # 要求：必须是【已经借到手上的书】
    global students
    date = generate_date()
    stu = get_student_with_books()
    if stu is None:
        return
    else:
        merged_set = students[stu]['B'].union(students[stu]['C'])
        book = random.sample(merged_set, 1)[0]
    # 在最开始，先处理堆积的预约
    handle_arrange()
    # 再加入新指令
    line = ''.join(f'[{date}] {stu} returned {book}')
    data_list.append(line)
    handle_return(stu, book)


def try_to_smear():
    # 要求：必须是【已经借到手上的书】
    # 策略：损毁后立即归还，且强制使时间往后推移 3 天，以保证下一条指令到来时必定已上架
    global cur_date, students
    date = generate_date()
    stu = get_student_with_books()
    if stu is None:
        return
    else:
        merged_set = students[stu]['B'].union(students[stu]['C'])
        book = random.sample(merged_set, 1)[0]
    # 在最开始，先处理堆积的预约
    handle_arrange()
    # 再加入新指令
    line = ''.join(f'[{date}] {stu} smeared {book}')
    data_list.append(line)
    line = ''.join(f'[{date}] {stu} returned {book}')
    data_list.append(line)
    handle_return(stu, book, 'smeared')
    # date += 3 compulsively
    generate_date(3)


def try_to_lose():
    # 要求：必须是【已经借到手上的书】
    global students
    date = generate_date()
    stu = get_student_with_books()
    if stu is None:
        return
    else:
        merged_set = students[stu]['B'].union(students[stu]['C'])
        book = random.sample(merged_set, 1)[0]
    # 在最开始，先处理堆积的预约
    handle_arrange()
    # 再加入新指令
    line = ''.join('[{0}] {1} lost {2}'.format(date, stu, book))
    data_list.append(line)
    students[stu][book.split('-')[0]].remove(book)
    handle_return(stu, book, 'lost')


# -------------------------------后台辅助函数----------------------------------
# 尽可能地获取一个【手上有书】的学生
def get_student_with_books():
    global students
    stu = random.choice(list(students.keys()))
    for i in range(20):
        stu = random.choice(list(students.keys()))
        if (len(students[stu]['B']) > 0) or (len(students[stu]['C']) > 0):
            break
        stu = None
    return stu


# 处理【借书】的情况
def handle_borrow(stu, book):
    global students, books, ans_list, res_list
    global cur_date, today_orders_count, last_arranged_date
    book_type = book.split('-')[0]
    # 无论能不能借到，都会 query
    someone = 'self-service machine'  # 缺省为自动机
    line = ''.join(f'[{cur_date}] {stu} queried {book} from {someone}')
    ans_list.append(line)
    # 开始借书
    if book_type == 'A':
        return
    prompt_res(cur_date, stu, 'tried to borrow', book)
    # 先将书取出
    if books[book] > 0:
        books[book] -= 1
        took_tag = True
    else:
        took_tag = False
    # 限制：持有某书后再继续借，或是持有 B 类书后再借 B 类书，必定拒绝
    if (book in students[stu]['B'] or book in students[stu]['C']) or \
            (book_type == 'B' and len(students[stu]['B']) > 0):
        prompt_res(cur_date, stu, 'failed to borrow', book, '- already had same type/book')
        # 如果有库存，会转入 unshelved；如果没库存，直接拒绝 order
        if took_tag:
            if book not in unshelved:
                unshelved[book] = 1
            else:
                unshelved[book] += 1
        return
    # 如果有库存，则可以直接借到
    if took_tag:
        students[stu][book_type].add(book)
        # borrowed successfully
        if book_type == 'B':  # 对缺省进行更改
            someone = 'borrowing and returning librarian'
        line = ''.join(f'[{cur_date}] {stu} borrowed {book} from {someone}')
        ans_list.append(line)
        # 特别地，检查请求队列，将相应受影响的请求移除
        if book_type == 'B':
            remove_b_type_order(stu, cur_date)
    # 如果没库存，则检查是否能加入请求队列，以等待下一次还书时通知
    else:
        prompt_res(cur_date, stu, 'failed to borrow', book, '- stock <= 0')
        prompt_res(cur_date, stu, 'tried to order', book)
        # 检查该学生今日预约数
        if stu not in today_orders_count:
            today_orders_count[stu] = 0
        elif today_orders_count[stu] >= 3:
            prompt_res(cur_date, stu, 'failed to order', book, '- orders >= 3')
            return
        today_orders_count[stu] += 1
        # 检查是否有重复预约
        order = {'stu': stu, 'book': book}
        if order in waiting_list:
            prompt_res(cur_date, stu, 'failed to order', book, '- already ordered')
            return
        # 检查是否重复持有
        if (book_type == 'B' and len(students[stu]['B']) > 0) \
                or (book_type == 'C' and book in students[stu]['C']):
            prompt_res(cur_date, stu, 'failed to order', book, '- already had same type/book')
            return
        # 可以借书
        waiting_list.append(order)
        # ordered successfully
        someone = 'ordering librarian'
        line = ''.join(f'[{cur_date}] {stu} ordered {book} from {someone}')
        ans_list.append(line)


# 处理【还书】的情况
def handle_return(stu, book, status='normal'):
    global students, books, unshelved, cur_date, ans_list, res_list, _res_store
    book_type = book.split('-')[0]
    # 先检查书籍状态，若有损毁或丢失，则需要罚款
    someone = 'borrowing and returning librarian'
    if status == 'smeared' or status == 'lost':
        line = ''.join(f'[{cur_date}] {stu} got punished by {someone}')
        ans_list.append(line)
        if status == 'lost':
            return
    # 开始还书
    students[stu][book_type].remove(book)
    # books[book] += 1
    if book not in unshelved:
        unshelved[book] = 1
    else:
        unshelved[book] += 1
    # returned successfully
    if book_type == 'C':
        someone = 'self-service machine'
    line = ''.join(f'[{cur_date}] {stu} returned {book} to {someone}')
    ans_list.append(line)
    if status == 'smeared':
        someone = 'logistics division'
        line = ''.join(f'[{cur_date}] {book} got repaired by {someone}')
        ans_list.append(line)


# 处理预约
def handle_arrange():
    global students, books, unshelved, waiting_list, res_list, _res_store
    # 在最开始，先检查是否需要整理
    arrange_tag, updated_date = get_arranged_date()
    if arrange_tag:
        # 通知预定的学生
        for order in list(waiting_list):
            stu = order['stu']
            book = order['book']
            book_type = book.split('-')[0]
            if book in unshelved and unshelved[book] > 0:
                unshelved[book] -= 1
                students[stu][book_type].add(book)
                waiting_list.remove(order)
                # borrowed successfully
                someone = 'ordering librarian'
                line = ''.join(f'[{updated_date}] {stu} borrowed {book} from {someone}')
                ans_list.append(line)
                # 移除冗余请求
                if book_type == 'B':
                    remove_b_type_order(stu, updated_date)
        # 上架 unshelved
        for book in unshelved:
            books[book] += unshelved[book]
            prompt_res(cur_date, 'arranging librarian', f'shelved {unshelved[book]}', book)
        unshelved = {}


# 移除所有 B 类请求
def remove_b_type_order(stu, date):
    global waiting_list, res_list
    for order in list(waiting_list):
        order_stu = order['stu']
        order_book = order['book']
        order_type = order_book.split('-')[0]
        if (order_stu == stu) and (order_type == 'B'):
            prompt_res(date, order_stu, 'canceled order of', order_book, '- already borrowed type B')
            waiting_list.remove(order)


# 获取下一个整理日，并更新最近的整理日
def get_arranged_date():
    global last_arranged_date
    delta_days = (cur_date - last_arranged_date).days
    if delta_days < 3:
        return False, last_arranged_date
    else:
        # align_down
        mod = delta_days % 3
        delta_days -= mod
        updated_date = last_arranged_date + timedelta(days=3)
        last_arranged_date += timedelta(days=delta_days)
        return True, updated_date


# 输出详细信息到 _res_file
def prompt_res(date, someone, behavior, obj='', reason=''):
    global cur_date, books, res_list, _res_store
    if not _res_store:
        return
    line = ''.join(f'[{date}]: {someone} {behavior} {obj} {reason}')
    res_list.append(line)


# ------------------------主函数---------------------------
funcs = {
    try_to_borrow: 1,
    try_to_return: 1,
    try_to_smear: 1,
    try_to_lose: 1
}


def generate_data(books_account, operations_account,
                  input_text='input.txt', ans_text='ans.txt', res_text='res.txt', res_store=True):
    # init
    global books, unshelved, students, waiting_list
    global data_list, ans_list, res_list
    global cur_date, max_date_limit, last_arranged_date, today_orders_count
    global _data_file, _ans_file, _res_file, _res_store
    _data_file = input_text
    _ans_file = ans_text
    _res_file = res_text
    _res_store = res_store

    data_list = []
    ans_list = []
    res_list = []
    books = {}
    unshelved = {}
    students = {}
    waiting_list = deque()
    cur_date = datetime(2023, 1, 1).date()
    last_arranged_date = datetime(2023, 1, 1).date()
    max_date_limit = (operations_account <= 100)
    today_orders_count = {}

    students_account = int(operations_account / 3)

    generate_books(books_account)
    generate_students(students_account)

    data_list.append(str(operations_account))
    ori_len = len(data_list)
    cur_len = ori_len
    while cur_len < ori_len + operations_account:
        rand_func = random.choices(list(funcs.keys()), weights=list(funcs.values()))[0]
        if cur_len == ori_len + operations_account - 1:
            while rand_func == try_to_smear:
                rand_func = random.choices(list(funcs.keys()), weights=list(funcs.values()))[0]
        rand_func()
        cur_len = len(data_list)

    with open(_data_file, 'w') as f1, open(_ans_file, 'w') as f2:
        f1.write("\n".join(data_list))
        f2.write("\n".join(ans_list))
    if _res_store:
        with open(_res_file, 'w') as f3:
            f3.write("\n".join(res_list))
