# Copyright 2025 Yingwei Zheng
# SPDX-License-Identifier: Apache-2.0

import json
import sys


def convert_operand_list(args):
    res = []
    for arg, identifier in args:
        res.append(f"{arg['printable']}:{identifier}")
    return res

def encode_var_bit(var, msb, lsb):
    if msb == lsb:
        return var + '{' + str(msb) + '}'
    return var + '{' + str(msb) + '-' + str(lsb) + '}'

def encode_inst(encoding):
    bit_string = ""
    var = None
    var_msb = None
    var_lsb = None
    for bit in reversed(encoding):
        if isinstance(bit, int):
            if var:
                bit_string += encode_var_bit(var, var_msb, var_lsb)
                var = None
            bit_string += str(bit)
        elif bit['kind'] == 'var':
            bit_string += bit['var']
        else:
            assert bit['kind'] == 'varbit'
            new_var = bit['var']
            new_idx = bit['index']
            if var is None:
                var = new_var
                var_msb = var_lsb = new_idx
            elif var == new_var and new_idx + 1 == var_lsb:
                var_lsb = new_idx
            else:
                bit_string += encode_var_bit(var, var_msb, var_lsb)
                var = new_var
                var_msb = var_lsb = new_idx
    return bit_string

if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        obj = json.load(f)
    for item in obj.values():
        if not isinstance(item, dict):
            continue
        if item.get("!anonymous", True):
            continue
        name = item.get("!name")
        if not name:
            continue
        fields = item.get("!fields", [])
        if "Inst" in fields:
            if item["isCodeGenOnly"] == 1:
                continue
            if item["isPseudo"] == 1:
                continue
            if item["isPreISelOpcode"] == 1:
                continue
            # print(json.dumps(item, indent=2))
            inst_obj = dict()
            inst_obj["Name"] = name
            inst_obj["Size"] = item["Size"]
            inst_obj["AsmString"] = item["AsmString"]
            if item["DecoderNamespace"] != "":
                inst_obj["DecoderNamespace"] = item["DecoderNamespace"]
            if item["Constraints"] != "":
                inst_obj["Constraints"] = item["Constraints"]

            in_ops = convert_operand_list(item["InOperandList"]["args"])
            if len(in_ops) > 0:
                inst_obj["Inputs"] = in_ops
            out_ops = convert_operand_list(item["OutOperandList"]["args"])
            if len(out_ops) > 0:
                inst_obj["Outputs"] = out_ops
            predicates = []
            for pred in item["Predicates"]:
                predicates.append(pred["printable"])
            if len(predicates) > 0:
                inst_obj["Predicates"] = predicates
            inst_obj["Encoding"] = encode_inst(item["Inst"])

            properties_list = [
                "isReturn",
                "isBranch",
                "isEHScopeReturn",
                "isIndirectBranch",
                "isCompare",
                "isMoveImm",
                "isMoveReg",
                "isBitcast",
                "isSelect",
                "isBarrier",
                "isCall",
                "isAdd",
                "isTrap",
                "mayLoad",
                "mayStore",
                "mayRaiseFPException",
                "isTerminator",
                "hasDelaySlot",
                "hasCtrlDep",
                "isNotDuplicable",
                "isConvergent",
                "isAsCheapAsAMove",
                "hasSideEffects",
            ]
            properties = []
            for key in properties_list:
                if item.get(key, False):
                    properties.append(key)
            if len(properties) > 0:
                inst_obj["Properties"] = properties
            print(json.dumps(inst_obj, indent=2))
            # exit()
