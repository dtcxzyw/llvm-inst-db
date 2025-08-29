# Copyright 2025 Yingwei Zheng
# SPDX-License-Identifier: Apache-2.0

import json
import sys
import subprocess
import tqdm
import os
from targets import SUPPORTED_TARGETS

PROPERTIES_LIST = [
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


def convert_operand_list(args):
    res = []
    for arg, identifier in args:
        res.append(f"{arg['printable']}:{identifier}")
    return res


def encode_var_bit(var, msb, lsb):
    if msb == lsb:
        return var + "[" + str(msb) + "]"
    return var + "[" + str(msb) + ":" + str(lsb) + "]"


def encode_inst(encoding):
    bit_string = ""
    var = None
    var_msb = None
    var_lsb = None
    for bit in reversed(encoding):
        if bit is None:
            bit_string += "?"
        elif isinstance(bit, int):
            if var:
                bit_string += encode_var_bit(var, var_msb, var_lsb)
                var = None
            bit_string += str(bit)
        elif bit["kind"] == "var":
            bit_string += bit["var"] + '[0]'
        elif bit["kind"] == "varbit":
            new_var = bit["var"]
            new_idx = bit["index"]
            if var is None:
                var = new_var
                var_msb = var_lsb = new_idx
            elif var == new_var and new_idx + 1 == var_lsb:
                var_lsb = new_idx
            else:
                bit_string += encode_var_bit(var, var_msb, var_lsb)
                var = new_var
                var_msb = var_lsb = new_idx
        else:
            assert bit["kind"] == "complex"
            return None
    return bit_string


def convert_json(target, input_json, output_json):
    with open(input_json) as f:
        obj = json.load(f)
    inst_list = []
    for item in tqdm.tqdm(obj.values()):
        if not isinstance(item, dict):
            continue
        if item.get("!anonymous", True):
            continue
        name = item.get("!name")
        if not name:
            continue
        fields = item.get("!fields", [])
        superclasses = item.get("!superclasses", [])
        if "Inst" in fields or "Instruction" in superclasses:
            if item["isCodeGenOnly"] == 1:
                continue
            if item["isPseudo"] == 1:
                continue
            if item["isPreISelOpcode"] == 1:
                continue
            # print(json.dumps(item, indent=2))
            inst_obj = dict()
            inst_obj["Name"] = name
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
            if "Inst" in item:
                inst_obj["Size"] = item["Size"]
                inst_encoding = encode_inst(item["Inst"])
                if inst_encoding:
                    inst_obj["Encoding"] = inst_encoding
            elif "X86Inst" in superclasses:
                # TODO: handle X86 inst prefixes
                pass

            properties = []
            for key in PROPERTIES_LIST:
                if item.get(key, False):
                    properties.append(key)
            if len(properties) > 0:
                inst_obj["Properties"] = properties
            inst_list.append(inst_obj)
    inst_list.sort(key=lambda x: x["Name"])
    obj = {
        "Target": target,
        "Insts": inst_list,
    }
    with open(output_json, "w") as f:
        json.dump(obj, f)


if __name__ == "__main__":
    llvm_src = sys.argv[1]
    llvm_tblgen = sys.argv[2]
    build_dir = "build"
    os.makedirs(build_dir, exist_ok=True)
    original_dir = os.path.join(build_dir, "original")
    os.makedirs(original_dir, exist_ok=True)
    artifact_dir = os.path.join(build_dir, "artifact")
    os.makedirs(artifact_dir, exist_ok=True)
    include_dir = os.path.join(llvm_src, "llvm/include")
    for target in SUPPORTED_TARGETS:
        print("Converting", target)
        intermediate_json = os.path.join(original_dir, target + ".json")
        target_dir = os.path.join(llvm_src, "llvm/lib/Target", target)
        target_td = target + ".td"
        if target == "PowerPC":
            target_td = "PPC.td"
        if not os.path.exists(intermediate_json):
            subprocess.check_call(
                [
                    llvm_tblgen,
                    "--dump-json",
                    os.path.join(target_dir, target_td),
                    "-o",
                    intermediate_json,
                    "-I",
                    include_dir,
                    "-I",
                    target_dir,
                ]
            )
        artifact_json = os.path.join(artifact_dir, target + ".json")
        convert_json(target, intermediate_json, artifact_json)
