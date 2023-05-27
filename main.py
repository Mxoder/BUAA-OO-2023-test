import os
import shutil
import threading

import generate_data
import setup

def get_input():
    is_defalut = (input("使用默认设置(y/n): "))
    if is_defalut != 'n' and is_defalut != 'N':
        check_rounds = setup.check_rounds
        books_account = setup.books_account
        operations_account = setup.operations_account
        input_store_dir = setup.input_store_dir
        output_store_dir = setup.output_store_dir
        ans_store_dir = setup.ans_store_dir
        res_store_dir = setup.res_store_dir
        clean_if_no_diff = setup.clean_if_no_diff
        store_operation_res = setup.store_operation_res
        max_threads = setup.max_threads
    else : 
        check_rounds = int(input("请输入测试轮数: "))
        books_account = int(input("请输入图书种类数: "))
        operations_account = int(input("请输入指令总数, 当总数大于100时, 日期会超过2023-12-31: "))
        input_store_dir = input("请输入输入数据存放的相对路径: ")
        output_store_dir = input("请输入程序输出存放的相对路径: ")
        ans_store_dir = input("请输入答案存放的相对路径: ")
        res_store_dir = input("请输入指令的详细模拟结果存放的相对路径: ")
        temp = (input("是否清除ac数据(y/n): "))
        clean_if_no_diff = (temp != 'N' and temp != "n")
        temp = (input("是否保存指令的详细模拟结果(y/n): "))
        store_operation_res = (temp != 'N' and temp != "n")
        max_threads = int(input("请输入线程数: "))
    return check_rounds, books_account, operations_account, input_store_dir, output_store_dir, ans_store_dir, res_store_dir, clean_if_no_diff, store_operation_res, max_threads
  
check_rounds, books_account, operations_account, input_store_dir, output_store_dir, ans_store_dir, res_store_dir, clean_if_no_diff, store_operation_res, max_threads = get_input()

jars = []
diff_res = {}


def make_dir(dir_path):
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)
    os.mkdir(dir_path)


class CheckThread(threading.Thread):
    def __init__(self, index, lock):
        threading.Thread.__init__(self)
        self.index = index + 1
        self.lock = lock

    def run(self):
        self.check()

    def check(self):
        global books_account, operations_account, input_store_dir, output_store_dir
        global ans_store_dir, res_store_dir, clean_if_no_diff, store_operation_res
        global jars, diff_res
        i = self.index
        input_file = f'{input_store_dir}/input_{i}.txt'
        ans_file = f'{ans_store_dir}/ans_{i}.txt'
        res_file = f'{res_store_dir}/res_{i}.txt'

        # generate data
        with self.lock:
            generate_data.generate_data(books_account, operations_account,
                                        input_file, ans_file, res_file, store_operation_res)

        # check
        diff_tag = False
        outputs = []
        for jar in jars:
            jar_name = jar.split('.')[0]
            output_file = f'{output_store_dir}/{jar_name}/{jar_name}_out_{i}.txt'
            outputs.append(output_file)
            os.system(f'java -jar {jar} < {input_file} > {output_file}')

            with open(output_file, "r") as f1, open(ans_file, "r") as f2:
                if f1.read().strip() != f2.read().strip():
                    diff_tag = True
                    print(f'round {i}, {jar_name} diff!')
                    if jar not in diff_res:
                        diff_res[jar] = 1
                    else:
                        diff_res[jar] += 1

        # clean
        if clean_if_no_diff and not diff_tag:
            os.remove(input_file)
            for output in outputs:
                os.remove(output)
            os.remove(ans_file)
            if store_operation_res:
                os.remove(res_file)

        # prompt
        if i % 10 == 0:
            print(f'checked {i} rounds...')


if __name__ == '__main__':
    # make directories, if existed, then empty
    make_dir(input_store_dir)
    make_dir(output_store_dir)
    make_dir(ans_store_dir)
    if store_operation_res:
        make_dir(res_store_dir)

    # get all jars
    jars = []
    for file in os.listdir():
        if file.endswith('.jar'):
            jars.append(file)
            jar_name = file.split('.')[0]
            make_dir(f'{output_store_dir}/{jar_name}')

    # set threads
    threads = []
    groups = int(check_rounds / max_threads) + 1
    locks = [threading.Lock() for _ in range(max_threads)]

    # start check
    diff_res = {}
    print('start checking')
    print('checked jars:' + ' '.join(jars))
    print(f'total rounds: {check_rounds}')
    print(f'max_threads: {max_threads}')
    if clean_if_no_diff:
        print('Files with no differences will be deleted.')
    print('----------------check start---------------------------')

    for i in range(groups):
        for j in range(max_threads):
            if i * max_threads + j >= check_rounds:
                break
            t = CheckThread(i * max_threads + j, locks[i % max_threads])
            threads.append(t)
        for t in threads[i * max_threads:i * max_threads + max_threads]:
            t.start()
        for t in threads[i * max_threads:i * max_threads + max_threads]:
            t.join()

    # end
    print('---------------------check end----------------------------\nresult:')
    for jar in jars:
        if jar not in diff_res:
            print(f'{jar}: All success!')
        else:
            print(f'{jar}: diff {diff_res[jar]} times')
    os.system('pause')