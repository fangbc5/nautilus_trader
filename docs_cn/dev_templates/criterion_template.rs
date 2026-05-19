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

// 本文件为英文版本（../../docs/dev_templates/criterion_template.rs）的中文注释版本。

//! Criterion 基准测试模板。
//!
//! 将本文件复制到 `crates/<my_crate>/benches/` 目录下，并根据需要调整名称
//! 与 import 语句。使用以下命令编译运行：
//!
//! ```bash
//! cargo bench -p <my_crate> --bench <file_stem>
//! ```

use std::hint::black_box;

use criterion::{criterion_group, criterion_main, Criterion};

// -----------------------------------------------------------------------------
// 将 `my_function` 与准备数据的代码替换为你的真实工作负载。
// -----------------------------------------------------------------------------

fn my_function(input: &[u8]) -> usize {
    input.iter().map(|b| *b as usize).sum()
}

fn prepare_data() -> Vec<u8> {
    (0u8..=255).collect()
}

fn bench_my_function(c: &mut Criterion) {
    let data = prepare_data();

    c.bench_function("my_function", |b| {
        b.iter(|| {
            let _ = black_box(my_function(&data));
        });
    });
}

criterion_group!(benches, bench_my_function);
criterion_main!(benches);
