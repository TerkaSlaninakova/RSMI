
import sys, getopt

import matplotlib.pyplot as plt
from dqn import DeepQNetwork
from ddpg import DeepDeterministicPolicyGradient
import numpy as np
import copy
import pandas as pd
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import logging
logging.getLogger('tensorflow').disabled = True  # this works to disable the WARNINGS

def cal_dist(source_cdf, target_cdf):
    max_dist = 0.0
    length = len(source_cdf)
    for i in range(length):
        temp_dist = abs(source_cdf[i] - target_cdf[i])
        if max_dist < temp_dist:
            max_dist = temp_dist
    return max_dist

def cal_reward(source_cdf, target_cdf):
    length = len(source_cdf)
    max_err = 0.0
    for i in range(length):
        if abs(source_cdf[i] - target_cdf[i]) > max_err:
            max_err = abs(source_cdf[i] - target_cdf[i])
    return max_err
    # length = len(source_cdf)
    # res = 0.0
    # for i in range(length):
    #     res += abs(source_cdf[i] - target_cdf[i])
    # return res / length

def init_sfc(length):
    pdf = [1.0 / length for i in range(length)]
    cdf = []
    num = 0.0
    sfc = [1 for i in range(length)]
    for item in pdf:
        num += item
        cdf.append(num)
    return pdf, cdf, sfc

def get_pdf_cdf_from_sfc(sfc, print_gap = False):
    length = sum(sfc)
    pdf = [i * 1.0 / length for i in sfc]
    cdf = []
    num = 0.0
    for item in pdf:
        num += item
        cdf.append(num)
    # TODO change cdf
    start_index = 0
    start = cdf[start_index]
    for i in range(1, len(cdf)):
        if cdf[i] == start:
            continue
        else:
            if (i - start_index) > 1:
                gap = (cdf[i] - start) / (i - start_index)
                if print_gap:
                    print("start_index",start_index)
                    print("cdf[start_index]",cdf[start_index])
                    print("i",i)
                    print("cdf[i]",cdf[i])
                for j in range(1, i - start_index):
                    # print("before cdf[start_index + j]", cdf[start_index + j])
                    cdf[start_index + j] += gap * j
                    # print("after cdf[start_index + j]", cdf[start_index + j])
            start_index = i
            start = cdf[start_index]
    return pdf, cdf

def get_pdf_cdf(path):
    pdf = []
    cdf = []
    with open(path, "r") as f:
        for line in f:
            cols = line.strip().split(",")
            pdf_item = float(cols[0])
            cdf_item = float(cols[1])
            cdf.append(cdf_item)
            pdf.append(pdf_item)
    return pdf, cdf

def choose_RL(name, length):
    if name == 'dqn':
        RL = DeepQNetwork(length, length)
    elif name == 'ddpg':
        REPLACEMENT = [
                dict(name='soft', tau=0.01),
                dict(name='hard', rep_iter_a=600, rep_iter_c=500)
            ][0]
        LR_A=0.01
        LR_C=0.01
        GAMMA=0.9
        EPSILON=0.1
        VAR_DECAY=.9995
        RL = DeepDeterministicPolicyGradient(length, length, 1, LR_A, LR_C, REPLACEMENT, GAMMA,
                                                EPSILON)
    return RL

def train_sfc(RL, sfc, cdf, target_cdf):
    # print("target_cdf", target_cdf)
    iteration = 10000
    MEMORY_CAPACITY=10000
    step = 0
    min_dist = 1.0
    min_sfc = []
    while True:
        source_pdf, source_cdf = get_pdf_cdf_from_sfc(sfc)
        action = RL.choose_action(np.array(sfc))
        sfc1 = copy.deepcopy(sfc)
        sfc1[action] = 0
        pdf1, cdf1 = get_pdf_cdf_from_sfc(sfc1)
        sfc2 = copy.deepcopy(sfc)
        sfc2[action] = 1
        pdf2, cdf2 = get_pdf_cdf_from_sfc(sfc2)
        dist = cal_reward(source_cdf, target_cdf)
        dist1 = cal_reward(cdf1, target_cdf)
        dist2 = cal_reward(cdf2, target_cdf)

        if sfc[action] == 0:
            if dist1 < dist2:
                reward = -0.1 # TODO change this -0.001
                sfc_new = sfc1
            else:
                reward = dist1 - dist2
                sfc_new = sfc2
            RL.store_transition(np.array(sfc), action, reward, np.array(sfc2))
            reward = 0
            RL.store_transition(np.array(sfc), action, reward, np.array(sfc1))
        else:
            if dist1 < dist2:
                reward = dist2 - dist1
                sfc_new = sfc1
            else:
                reward = -0.1
                sfc_new = sfc2
            RL.store_transition(np.array(sfc), action, reward, np.array(sfc1))
            reward = 0
            RL.store_transition(np.array(sfc), action, reward, np.array(sfc2))
        if (step > MEMORY_CAPACITY) and (step % 10 == 0):
            RL.learn()
        temp_dist = cal_dist(source_cdf, target_cdf)
        if temp_dist < min_dist:
            min_dist = temp_dist
            min_sfc = sfc_new
        if step > iteration:
            print(temp_dist)
            break
        sfc = sfc_new
        # if step % 100 == 0:
        #     print("min_dist", min_dist)
        #     print("step", step)
            # new_pdf, new_cdf = get_pdf_cdf_from_sfc(sfc)
            # print("new_sfc", sfc)
            # print("new_cdf", new_cdf)
        step += 1
    print(min_dist)
    return min_sfc, min_dist
    # return sfc

def load_data(name):
    data = pd.read_csv(name, header=None)
    x = data[0].values.reshape(-1, 1)
    y = data[1].values.reshape(-1, 1)
    return x, y

def draw_cdf_8t8(source_cdfs, new_cdfs, target_cdfs, labels):
    col_num = len(source_cdfs)
    for i in range(col_num):
        length = len(source_cdfs[i])
        x = [(i) * 1.0 / (length-1) for i in range(length)]
        plt.plot(x, new_cdfs[i], label="real")
        # plt.title(labels[i])
    resolution = 54
    x, y = load_data('/home/liuguanli/Documents/pre_train/features_zm/' + str(resolution) + '_OSM_100000000_1_2_.csv')
    side = int(pow(2, resolution / 2))
    plt.plot(x, y, label="synthetic")

    plt.legend(fontsize=20, loc="best", ncol=1)

    plt.savefig("sfcs.png", format='png', bbox_inches='tight')
    plt.savefig("sfcs.eps", format='eps', bbox_inches='tight')
    plt.show()

def draw_cdf(source_cdfs, new_cdfs, target_cdfs, labels):
    col_num = len(source_cdfs)
    for i in range(col_num):
        length = len(source_cdfs[i])
        x = [(i+1) * 1.0 / length for i in range(length)]
        
        plt.subplot(col_num, 3, i * 3 + 1)
        plt.plot(x, source_cdfs[i])
        

        plt.subplot(col_num, 3, i * 3 + 2)
        plt.plot(x, new_cdfs[i])

        plt.title(labels[i])

        plt.subplot(col_num, 3, i * 3 + 3)
        plt.plot(x, target_cdfs[i])
    plt.subplots_adjust(hspace=1.5, wspace=0.5)
    plt.savefig("sfcs.png", format='png', bbox_inches='tight')
    plt.show()

def run(file_name, method_name):
    target_pdf, target_cdf = get_pdf_cdf(file_name)
    length = len(target_cdf)
    sfc = [1 for i in range(length)]
    source_pdf, source_cdf = get_pdf_cdf_from_sfc(sfc)
    new_sfc, min_dist = train_sfc(choose_RL(method_name, length), sfc, source_cdf, target_cdf)
    new_pdf, new_cdf = get_pdf_cdf_from_sfc(new_sfc)
    # print("new_cdf", new_cdf)
    # print("new_sfc", new_sfc)
    return source_cdf, new_cdf, target_cdf, min_dist, new_sfc

def write_SFC(bit_num, sfc, cdf):
    all_fo = open("/home/liuguanli/Documents/pre_train/sfc_z/bit_num_" + str(bit_num) + ".csv", "w")
    num = len(sfc)
    for i in range(num):
        all_fo.write(str(sfc[i]) + "," + str(cdf[i]) + "\n")
    all_fo.close()

def parser(argv):
    try:
        opts, args = getopt.getopt(argv, "d:s:n:m:b:f:")
    except getopt.GetoptError:
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-d':
            distribution = arg
        elif opt == '-s':
            size = int(arg)
        elif opt == '-n':
            skewness = int(arg)
        elif opt == '-m':
            dim = int(arg)
        elif opt == '-b':
            bit_num = int(arg)
        elif opt == '-f':
            filename = arg
    return distribution, size, skewness, dim, bit_num, filename
    # filename = filename % (bit_num, distribution, size, skewness, dim)
    
def run_demo(method_name = 'ddpg'):
    # target_pdf, target_cdf = get_pdf_cdf(file_name)
    target_cdf = [
    1/16,1/16,1/16,1/16,1/16,1/16,2/16,2/16,2/16,3/16,3/16,3/16,4/16,5/16,5/16,5/16,5/16,
    5/16,5/16,5/16,5/16,5/16,5/16,5/16,5/16,5/16,5/16,5/16,6/16,6/16,6/16,7/16,7/16,7/16,
    8/16,8/16,8/16,8/16,9/16,10/16,11/16,11/16,11/16,11/16,11/16,11/16,11/16,11/16,11/16,
    12/16,12/16,12/16,12/16,12/16,12/16,12/16,12/16,12/16,13/16,13/16,14/16,14/16,15/16,16/16]
    target_pdf = []
    length = len(target_cdf)
    sfc = [1 for i in range(length)]
    source_pdf, source_cdf = get_pdf_cdf_from_sfc(sfc)
    new_sfc, min_dist = train_sfc(choose_RL(method_name, length), sfc, source_cdf, target_cdf)
    new_pdf, new_cdf = get_pdf_cdf_from_sfc(new_sfc)
    print("new_sfc", new_sfc)
    print("new_cdf", new_cdf)
    return source_cdf, new_cdf, target_cdf, min_dist, new_sfc

def run_exp(parameters):
    distribution, size, skewness, dim, bit_num, file_name_pattern = parser(parameters)
    source_cdfs = []
    new_cdfs = []
    target_cdfs = []
    labels = []
    # bit_nums = [6, 8, 10]
    bit_nums = [6]
    # method_names = ['dqn', 'ddpg']
    method_names = ['dqn']
    for bit_num in bit_nums:
        for method_name in method_names:
            source_cdf, new_cdf, target_cdf, min_dist, new_sfc = run(file_name_pattern % (bit_num, distribution, size, skewness, dim), method_name)
            write_SFC(bit_num, new_sfc, new_cdf)
            source_cdfs.append(source_cdf)
            new_cdfs.append(new_cdf)
            target_cdfs.append(target_cdf)
            labels.append(method_name + "-" + str(pow(2, bit_num)) + " cells    dist=" + str(min_dist))
    # draw_cdf(source_cdfs, new_cdfs, target_cdfs, labels)
    # draw_cdf_8t8(source_cdfs, new_cdfs, target_cdfs, labels)

if __name__ == "__main__":
    run_exp(sys.argv[1:])
    # run_demo()
    # python /home/liuguanli/Dropbox/shared/VLDB20/codes/rsmi/pre-train/rl_4_sfc/RL_4_SFC.py -d uniform -s 64000000 -n 1 -m 2 -b 6 -f /home/liuguanli/Documents/pre_train/sfc_z_weight/bit_num_%d/%s_%d_%d_%d_.csv



# target_cdf [0.0301679, 0.0930956, 0.100308, 0.115298, 0.218105, 0.349468, 0.373981, 0.405233, 0.408832, 0.41634, 0.41841, 0.422742, 0.434991, 0.450669, 0.457727, 0.466734, 0.597975, 0.700751, 0.732043, 0.756522, 0.819519, 0.849736, 0.86473, 0.871919, 0.887568, 0.899804, 0.908826, 0.915893, 0.923402, 0.926999, 0.931313, 0.933378, 0.934668, 0.937354, 0.938184, 0.939929, 0.944287, 0.949866, 0.952705, 0.956338, 0.956905, 0.958074, 0.958463, 0.959279, 0.961214, 0.963663, 0.964993, 0.96669, 0.972259, 0.976641, 0.980274, 0.983118, 0.9858, 0.987089, 0.988825, 0.989662, 0.992115, 0.994026, 0.995724, 0.997059, 0.998233, 0.998799, 0.999612, 1.0]
# min_dist 0.505986
# step 0
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
# new_cdf [0.015873015873015872, 0.031746031746031744, 0.047619047619047616, 0.06349206349206349, 0.07936507936507936, 0.09523809523809523, 0.1111111111111111, 0.12698412698412698, 0.14285714285714285, 0.15873015873015872, 0.1746031746031746, 0.19047619047619047, 0.20634920634920634, 0.2222222222222222, 0.23809523809523808, 0.25396825396825395, 0.2698412698412698, 0.2857142857142857, 0.30158730158730157, 0.31746031746031744, 0.3333333333333333, 0.3492063492063492, 0.36507936507936506, 0.38095238095238093, 0.3968253968253968, 0.4126984126984127, 0.42857142857142855, 0.4444444444444444, 0.4603174603174603, 0.47619047619047616, 0.49206349206349204, 0.5079365079365079, 0.5238095238095237, 0.5396825396825395, 0.5555555555555554, 0.5714285714285712, 0.587301587301587, 0.6031746031746028, 0.6190476190476186, 0.6349206349206344, 0.6507936507936503, 0.6666666666666661, 0.6825396825396819, 0.6904761904761898, 0.6984126984126977, 0.7142857142857135, 0.7301587301587293, 0.7460317460317452, 0.761904761904761, 0.7777777777777768, 0.7936507936507926, 0.8095238095238084, 0.8253968253968242, 0.8412698412698401, 0.8571428571428559, 0.8730158730158717, 0.8888888888888875, 0.9047619047619033, 0.9206349206349191, 0.936507936507935, 0.9523809523809508, 0.9682539682539666, 0.9841269841269824, 0.9999999999999982]
# min_dist 0.45120436363636357
# step 100
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1]
# new_cdf [0.01818181818181818, 0.03636363636363636, 0.05454545454545454, 0.07272727272727272, 0.09090909090909091, 0.1090909090909091, 0.1272727272727273, 0.14545454545454548, 0.16363636363636366, 0.18181818181818185, 0.20000000000000004, 0.21818181818181823, 0.23636363636363641, 0.2545454545454546, 0.27272727272727276, 0.29090909090909095, 0.30909090909090914, 0.3272727272727273, 0.3454545454545455, 0.3636363636363637, 0.3818181818181819, 0.4000000000000001, 0.41818181818181827, 0.42727272727272736, 0.43636363636363645, 0.45454545454545464, 0.47272727272727283, 0.490909090909091, 0.5090909090909091, 0.5151515151515152, 0.5212121212121212, 0.5272727272727273, 0.5454545454545455, 0.5636363636363637, 0.5818181818181819, 0.6000000000000001, 0.6090909090909091, 0.6181818181818183, 0.6363636363636365, 0.6545454545454547, 0.6727272727272728, 0.690909090909091, 0.7090909090909092, 0.7181818181818183, 0.7272727272727274, 0.7454545454545456, 0.7636363636363638, 0.781818181818182, 0.790909090909091, 0.8000000000000002, 0.8181818181818183, 0.8363636363636365, 0.8545454545454547, 0.8727272727272729, 0.8909090909090911, 0.9090909090909093, 0.9272727272727275, 0.9454545454545457, 0.9636363636363638, 0.981818181818182, 0.9863636363636366, 0.9909090909090912, 0.9954545454545457, 1.0000000000000002]
# min_dist 0.3816508936170216
# step 200
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1]
# new_cdf [0.021739130434782608, 0.043478260869565216, 0.06521739130434782, 0.08695652173913043, 0.10869565217391304, 0.13043478260869565, 0.15217391304347827, 0.17391304347826086, 0.19565217391304346, 0.21739130434782605, 0.23913043478260865, 0.26086956521739124, 0.28260869565217384, 0.30434782608695643, 0.326086956521739, 0.3478260869565216, 0.3695652173913042, 0.3913043478260868, 0.4130434782608694, 0.434782608695652, 0.4565217391304346, 0.4782608695652172, 0.4999999999999998, 0.5108695652173911, 0.5217391304347824, 0.543478260869565, 0.5652173913043476, 0.5869565217391302, 0.5923913043478258, 0.5978260869565215, 0.6032608695652171, 0.6086956521739127, 0.6304347826086953, 0.6413043478260867, 0.6521739130434779, 0.6594202898550722, 0.6666666666666663, 0.6739130434782605, 0.6956521739130431, 0.7173913043478257, 0.7391304347826083, 0.7608695652173909, 0.7826086956521735, 0.7898550724637677, 0.7971014492753619, 0.8043478260869561, 0.8097826086956518, 0.8152173913043474, 0.820652173913043, 0.8260869565217387, 0.8478260869565213, 0.8695652173913039, 0.8913043478260865, 0.9130434782608691, 0.9202898550724633, 0.9275362318840574, 0.9347826086956517, 0.945652173913043, 0.9565217391304343, 0.9782608695652169, 0.9836956521739125, 0.9891304347826082, 0.9945652173913038, 0.9999999999999994]
# min_dist 0.26594637837837853
# step 300
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0]
# new_cdf [0.02702702702702703, 0.05405405405405406, 0.08108108108108109, 0.10810810810810811, 0.13513513513513514, 0.16216216216216217, 0.1891891891891892, 0.21621621621621623, 0.24324324324324326, 0.2702702702702703, 0.2972972972972973, 0.32432432432432434, 0.35135135135135137, 0.3783783783783784, 0.40540540540540543, 0.43243243243243246, 0.4594594594594595, 0.4864864864864865, 0.5135135135135136, 0.5405405405405406, 0.5675675675675675, 0.5945945945945945, 0.6036036036036035, 0.6126126126126125, 0.6216216216216215, 0.6486486486486485, 0.6756756756756754, 0.7027027027027024, 0.7094594594594592, 0.7162162162162159, 0.7229729729729726, 0.7297297297297294, 0.7567567567567564, 0.7621621621621617, 0.7675675675675672, 0.7729729729729725, 0.778378378378378, 0.7837837837837833, 0.8108108108108103, 0.8175675675675671, 0.8243243243243238, 0.8310810810810805, 0.8378378378378373, 0.8416988416988411, 0.845559845559845, 0.8494208494208488, 0.8532818532818527, 0.8571428571428565, 0.8610038610038604, 0.8648648648648642, 0.8918918918918912, 0.9189189189189182, 0.9243243243243235, 0.929729729729729, 0.9351351351351344, 0.9405405405405398, 0.9459459459459452, 0.9594594594594587, 0.9729729729729721, 0.9999999999999991, 0.9999999999999991, 0.9999999999999991, 0.9999999999999991, 0.9999999999999991]
# min_dist 0.21109741176470587
# step 400
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]
# new_cdf [0.029411764705882353, 0.058823529411764705, 0.08823529411764705, 0.11764705882352941, 0.14705882352941177, 0.17647058823529413, 0.2058823529411765, 0.23529411764705885, 0.2647058823529412, 0.29411764705882354, 0.3235294117647059, 0.35294117647058826, 0.3823529411764706, 0.411764705882353, 0.44117647058823534, 0.4705882352941177, 0.5, 0.5294117647058824, 0.5588235294117647, 0.5882352941176471, 0.6176470588235294, 0.6470588235294118, 0.6568627450980392, 0.6666666666666667, 0.6764705882352942, 0.7058823529411765, 0.7352941176470589, 0.7647058823529412, 0.7705882352941177, 0.7764705882352941, 0.7823529411764707, 0.7882352941176471, 0.7941176470588236, 0.7990196078431373, 0.803921568627451, 0.8088235294117647, 0.8137254901960785, 0.8186274509803922, 0.823529411764706, 0.8308823529411765, 0.8382352941176472, 0.8455882352941178, 0.8529411764705883, 0.8571428571428572, 0.8613445378151261, 0.865546218487395, 0.869747899159664, 0.8739495798319329, 0.8781512605042018, 0.8823529411764707, 0.911764705882353, 0.9411764705882354, 0.9470588235294118, 0.9529411764705883, 0.9588235294117649, 0.9647058823529413, 0.9705882352941178, 0.9803921568627452, 0.9901960784313726, 1.0, 1.0, 1.0, 1.0, 1.0]
# min_dist 0.15423466666666674
# step 500
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]
# new_cdf [0.03333333333333333, 0.06666666666666667, 0.1, 0.13333333333333333, 0.16666666666666666, 0.19999999999999998, 0.2333333333333333, 0.26666666666666666, 0.3, 0.3333333333333333, 0.36666666666666664, 0.39999999999999997, 0.4333333333333333, 0.4666666666666666, 0.49999999999999994, 0.5333333333333333, 0.55, 0.5666666666666667, 0.6, 0.6333333333333333, 0.6666666666666666, 0.7, 0.711111111111111, 0.7222222222222222, 0.7333333333333333, 0.7666666666666666, 0.7833333333333332, 0.7999999999999999, 0.8022222222222222, 0.8044444444444444, 0.8066666666666666, 0.8088888888888888, 0.811111111111111, 0.8133333333333332, 0.8155555555555555, 0.8177777777777777, 0.82, 0.8222222222222222, 0.8244444444444444, 0.8266666666666665, 0.8288888888888888, 0.831111111111111, 0.8333333333333333, 0.838095238095238, 0.8428571428571427, 0.8476190476190475, 0.8523809523809524, 0.8571428571428571, 0.8619047619047618, 0.8666666666666666, 0.8999999999999999, 0.9333333333333332, 0.94, 0.9466666666666665, 0.9533333333333333, 0.9599999999999999, 0.9666666666666666, 0.9777777777777776, 0.9888888888888888, 0.9999999999999999, 0.9999999999999999, 0.9999999999999999, 0.9999999999999999, 0.9999999999999999]
# min_dist 0.1272457777777778
# step 600
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]
# new_cdf [0.037037037037037035, 0.07407407407407407, 0.1111111111111111, 0.14814814814814814, 0.18518518518518517, 0.2222222222222222, 0.25925925925925924, 0.2962962962962963, 0.3333333333333333, 0.37037037037037035, 0.4074074074074074, 0.42592592592592593, 0.4444444444444444, 0.48148148148148145, 0.5185185185185185, 0.5555555555555556, 0.5740740740740741, 0.5925925925925926, 0.6296296296296295, 0.6666666666666665, 0.7037037037037035, 0.7407407407407405, 0.7499999999999998, 0.759259259259259, 0.7685185185185182, 0.7777777777777775, 0.796296296296296, 0.8148148148148144, 0.8172839506172835, 0.8197530864197528, 0.8222222222222219, 0.824691358024691, 0.8271604938271601, 0.8296296296296293, 0.8320987654320984, 0.8345679012345675, 0.8370370370370366, 0.8395061728395058, 0.8419753086419749, 0.844444444444444, 0.8469135802469131, 0.8493827160493823, 0.8518518518518514, 0.8571428571428567, 0.862433862433862, 0.8677248677248672, 0.8730158730158726, 0.8783068783068778, 0.8835978835978832, 0.8888888888888884, 0.9074074074074069, 0.9259259259259254, 0.9333333333333328, 0.9407407407407402, 0.9481481481481475, 0.9555555555555549, 0.9629629629629624, 0.975308641975308, 0.9876543209876537, 0.9999999999999993, 0.9999999999999993, 0.9999999999999993, 0.9999999999999993, 0.9999999999999993]
# min_dist 0.11869876923076922
# step 700
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]
# new_cdf [0.038461538461538464, 0.07692307692307693, 0.11538461538461539, 0.15384615384615385, 0.19230769230769232, 0.23076923076923078, 0.2692307692307693, 0.3076923076923077, 0.34615384615384615, 0.3846153846153846, 0.423076923076923, 0.44230769230769224, 0.46153846153846145, 0.4999999999999999, 0.5384615384615383, 0.5769230769230768, 0.596153846153846, 0.6153846153846152, 0.6538461538461536, 0.6923076923076921, 0.7307692307692305, 0.7692307692307689, 0.7756410256410253, 0.7820512820512817, 0.7884615384615381, 0.7948717948717946, 0.801282051282051, 0.8076923076923074, 0.8102564102564099, 0.8128205128205125, 0.815384615384615, 0.8179487179487176, 0.8205128205128202, 0.8230769230769227, 0.8256410256410253, 0.8282051282051279, 0.8307692307692305, 0.833333333333333, 0.8358974358974356, 0.8384615384615381, 0.8410256410256407, 0.8435897435897433, 0.8461538461538458, 0.8516483516483513, 0.8571428571428568, 0.8626373626373622, 0.8681318681318678, 0.8736263736263733, 0.8791208791208788, 0.8846153846153842, 0.9038461538461535, 0.9230769230769227, 0.9307692307692303, 0.938461538461538, 0.9461538461538458, 0.9538461538461535, 0.9615384615384611, 0.9743589743589739, 0.9871794871794868, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996]
# min_dist 0.11869876923076922
# step 800
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]
# new_cdf [0.038461538461538464, 0.07692307692307693, 0.11538461538461539, 0.15384615384615385, 0.19230769230769232, 0.23076923076923078, 0.2692307692307693, 0.3076923076923077, 0.34615384615384615, 0.3846153846153846, 0.423076923076923, 0.44230769230769224, 0.46153846153846145, 0.4999999999999999, 0.5384615384615383, 0.5769230769230768, 0.596153846153846, 0.6153846153846152, 0.6538461538461536, 0.6923076923076921, 0.7307692307692305, 0.7692307692307689, 0.7756410256410253, 0.7820512820512817, 0.7884615384615381, 0.7948717948717946, 0.801282051282051, 0.8076923076923074, 0.8102564102564099, 0.8128205128205125, 0.815384615384615, 0.8179487179487176, 0.8205128205128202, 0.8230769230769227, 0.8256410256410253, 0.8282051282051279, 0.8307692307692305, 0.833333333333333, 0.8358974358974356, 0.8384615384615381, 0.8410256410256407, 0.8435897435897433, 0.8461538461538458, 0.8516483516483513, 0.8571428571428568, 0.8626373626373622, 0.8681318681318678, 0.8736263736263733, 0.8791208791208788, 0.8846153846153842, 0.9038461538461535, 0.9230769230769227, 0.9307692307692303, 0.938461538461538, 0.9461538461538458, 0.9538461538461535, 0.9615384615384611, 0.9743589743589739, 0.9871794871794868, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996]
# min_dist 0.11869876923076922
# step 900
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]
# new_cdf [0.038461538461538464, 0.07692307692307693, 0.11538461538461539, 0.15384615384615385, 0.19230769230769232, 0.23076923076923078, 0.2692307692307693, 0.3076923076923077, 0.34615384615384615, 0.3846153846153846, 0.423076923076923, 0.44230769230769224, 0.46153846153846145, 0.4999999999999999, 0.5384615384615383, 0.5769230769230768, 0.596153846153846, 0.6153846153846152, 0.6538461538461536, 0.6923076923076921, 0.7307692307692305, 0.7692307692307689, 0.7756410256410253, 0.7820512820512817, 0.7884615384615381, 0.7948717948717946, 0.801282051282051, 0.8076923076923074, 0.8102564102564099, 0.8128205128205125, 0.815384615384615, 0.8179487179487176, 0.8205128205128202, 0.8230769230769227, 0.8256410256410253, 0.8282051282051279, 0.8307692307692305, 0.833333333333333, 0.8358974358974356, 0.8384615384615381, 0.8410256410256407, 0.8435897435897433, 0.8461538461538458, 0.8516483516483513, 0.8571428571428568, 0.8626373626373622, 0.8681318681318678, 0.8736263736263733, 0.8791208791208788, 0.8846153846153842, 0.9038461538461535, 0.9230769230769227, 0.9307692307692303, 0.938461538461538, 0.9461538461538458, 0.9538461538461535, 0.9615384615384611, 0.9743589743589739, 0.9871794871794868, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996]
# min_dist 0.11869876923076922
# step 1000
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]
# new_cdf [0.038461538461538464, 0.07692307692307693, 0.11538461538461539, 0.15384615384615385, 0.19230769230769232, 0.23076923076923078, 0.2692307692307693, 0.3076923076923077, 0.34615384615384615, 0.3846153846153846, 0.423076923076923, 0.44230769230769224, 0.46153846153846145, 0.4999999999999999, 0.5384615384615383, 0.5769230769230768, 0.596153846153846, 0.6153846153846152, 0.6538461538461536, 0.6923076923076921, 0.7307692307692305, 0.7692307692307689, 0.7756410256410253, 0.7820512820512817, 0.7884615384615381, 0.7948717948717946, 0.801282051282051, 0.8076923076923074, 0.8102564102564099, 0.8128205128205125, 0.815384615384615, 0.8179487179487176, 0.8205128205128202, 0.8230769230769227, 0.8256410256410253, 0.8282051282051279, 0.8307692307692305, 0.833333333333333, 0.8358974358974356, 0.8384615384615381, 0.8410256410256407, 0.8435897435897433, 0.8461538461538458, 0.8516483516483513, 0.8571428571428568, 0.8626373626373622, 0.8681318681318678, 0.8736263736263733, 0.8791208791208788, 0.8846153846153842, 0.9038461538461535, 0.9230769230769227, 0.9307692307692303, 0.938461538461538, 0.9461538461538458, 0.9538461538461535, 0.9615384615384611, 0.9743589743589739, 0.9871794871794868, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996, 0.9999999999999996]
# 0.11869876923076922
# 0.11869876923076922
# new_sfc [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]