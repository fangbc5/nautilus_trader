// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  You may not use this file except in compliance with the License.
//  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// -------------------------------------------------------------------------------------------------

// 本文件为英文版本（../../docs/dev_templates/iai_template.rs）的中文注释版本。

//! iai 基准测试模板。
//!
//! 将本文件复制到 `crates/<my_crate>/benches/` 目录下，并根据需要调整名称
//! 与 import 语句。

use std::hint::black_box;

// -----------------------------------------------------------------------------
// 将 `fast_add` 替换为你想要测量的真实函数。
// -----------------------------------------------------------------------------

fn fast_add() -> i32 {
    let a = black_box(1);
    let b = black_box(2);
    a + b
}

iai::main!(fast_add);
