# Copyright 2025 Yingwei Zheng
# SPDX-License-Identifier: Apache-2.0

import json
import tqdm
import subprocess
import os
from targets import SUPPORTED_TARGETS


def parse_encoding(encoding: str) -> list:
    res = []
    i = 0
    bit_string = ""
    undef_string = ""
    while i != len(encoding):
        c = encoding[i]
        if c == "0" or c == "1":
            if undef_string != "":
                res.append({"bits": len(undef_string), "name": undef_string})
                undef_string = ""
            bit_string += c
            i += 1
        elif c == "?":
            if bit_string != "":
                res.append({"bits": len(bit_string), "name": bit_string})
                bit_string = ""
            undef_string += c
            i += 1
        else:
            if undef_string != "":
                res.append({"bits": len(undef_string), "name": undef_string})
                undef_string = ""
            if bit_string != "":
                res.append({"bits": len(bit_string), "name": bit_string})
                bit_string = ""
            subscript_beg = encoding.find("[", i)
            assert subscript_beg != -1
            subscript_end = encoding.find("]", subscript_beg)
            assert subscript_end != -1
            var_name = encoding[i:subscript_beg]
            index = encoding[subscript_beg + 1 : subscript_end]
            pos = index.find(":")
            if pos == -1:
                msb = lsb = int(index)
            else:
                msb = int(index[:pos])
                lsb = int(index[pos + 1 :])
            multi_use = encoding.count(var_name) > 1
            res.append(
                {
                    "bits": msb - lsb + 1,
                    "name": encoding[i : subscript_end + 1] if multi_use else var_name,
                }
            )
            i = subscript_end + 1
    if undef_string != "":
        res.append({"bits": len(undef_string), "name": undef_string})
        undef_string = ""
    if bit_string != "":
        res.append({"bits": len(bit_string), "name": bit_string})
        bit_string = ""
    return res


if __name__ == "__main__":
    build_dir = "build"
    os.makedirs(build_dir, exist_ok=True)
    artifact_dir = os.path.join(build_dir, "artifact")
    os.makedirs(artifact_dir, exist_ok=True)
    adoc_dir = os.path.join(build_dir, "adoc")
    os.makedirs(adoc_dir, exist_ok=True)
    html_dir = os.path.join(build_dir, "html")
    os.makedirs(html_dir, exist_ok=True)

    progress = tqdm.tqdm(SUPPORTED_TARGETS)
    for target in progress:
        progress.set_description(target)
        input_json = os.path.join(artifact_dir, f"{target}.json")
        output_adoc = os.path.join(adoc_dir, f"{target}.adoc")
        with open(input_json) as f:
            obj = json.load(f)
        insts = obj["Insts"]
        with open(output_adoc, "w") as out:
            out.write(f"== {target} Target\n")
            out.write("=== Instructions\n")
            for inst in insts:
                name = inst["Name"]
                out.write(f"==== {name}\n")
                asm_string = inst["AsmString"]
                for var in inst.get("Inputs", []) + inst.get("Outputs", []):
                    var_name = var[var.rfind(':') + 1:]
                    asm_string = asm_string.replace("${" + var_name + "}", var_name).replace("$" + var_name, var_name)
                out.write(f"[listing]\n----\n{asm_string}\n----\n")
                if "Encoding" in inst:
                    out.write("[wavedrom, , svg]\n....\n{reg: \n")
                    out.write(str(parse_encoding(inst["Encoding"])))
                    out.write(", config:{lanes: 1, hspace:1024}}\n....\n")
        output_html = os.path.join(html_dir, f"{target}.html")
        subprocess.check_call(
            [
                "asciidoctor",
                output_adoc,
                "-o",
                output_html,
                "--require=asciidoctor-diagram",
                "-a",
                "data-uri",
            ]
        )
