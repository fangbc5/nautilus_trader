# FFI 内存契约

> 本文档为 [English 原文](../../docs/developer_guide/ffi.md) 的中文翻译版本。如有歧义请以英文原版为准。

NautilusTrader 暴露了若干 **C 兼容** 类型，以便编译后的 Rust 代码可以被 Cython 生成的 C 扩展或其他原生语言所使用。其中最重要的是 `CVec` —— Rust `Vec<T>` 的一个*瘦*包装器，以**值传递**方式跨越 FFI 边界。

下面的规则是*严格*的；违反它们会导致未定义行为（通常是双重释放或内存泄漏）。

## FFI 边界上的快速失败 panic

Rust 的 panic 绝不应跨越 `extern "C"` 函数展开。让 panic 展开进入 C 或 Python 是未定义行为，可能破坏外部语言的栈，或留下未完全析构的资源。为强制执行快速失败架构，我们将每个导出的符号都包裹在 `crate::ffi::abort_on_panic` 中，它会执行函数体，并在发生 panic 时调用 `process::abort()`。Panic 消息在 abort 之前仍会被记录到日志中，因此在避免未定义行为的同时，保留了调试输出。

在添加新的 FFI 函数时，请使用 `abort_on_panic(|| { … })` 包裹实现（或使用执行同样工作的辅助函数）以维持该保证。

## CVec 生命周期

| 步骤  | 所有方                            | 动作 |
|-------|-----------------------------------|------|
| **1** | Rust                              | 构造一个 `Vec<T>` 并通过 `into()` 转换——这会*泄漏*该 vector，并将原始分配的所有权转移到外部代码。 |
| **2** | 外部（Python / Cython / C）       | 在 `CVec` 值的作用域内使用其数据。**不要修改 `ptr`、`len`、`cap` 字段。** |
| **3** | 外部                              | 恰好调用一次 Rust 导出的*类型特定*释放辅助函数（例如 `vec_drop_book_levels`、`vec_drop_book_orders`、`vec_time_event_handlers_drop`）。该辅助函数使用 `Vec::from_raw_parts` 重新构造原始的 `Vec<T>` 并让其析构，从而释放内存。 |

:::warning
如果遗漏了步骤 **3**，分配将在进程剩余生命周期内被泄漏；如果执行了**两次**，程序将出现双重释放，很可能崩溃。
:::

## 由 Python 侧创建的 capsule

部分 Cython 辅助函数会用 `PyMem_Malloc` 分配临时 C 缓冲区，将其包装为 `CVec`，并把地址封装在 `PyCapsule` 中返回。**每一个此类 capsule 都附带析构器**（`capsule_destructor` 或 `capsule_destructor_deltas`），它会同时释放缓冲区与 `CVec`。因此调用方*不得*手动释放内存——这样做会导致双重释放。

## 由 Rust 侧创建的 capsule *（PyO3 绑定）*

当 Rust 代码将堆分配的值传入 Python 时，**必须**使用 `PyCapsule::new_with_destructor`，这样 Python 才能在 capsule 不可达时知道如何释放该分配。闭包/析构器负责重新构造原始的 `Box<T>` 或 `Vec<T>` 并让其析构。

```rust
use pyo3::types::PyCapsule;

Python::attach(|py| {
    // Allocate the value on the heap
    let my_data = Box::new(MyStruct::new());
    let ptr = Box::into_raw(my_data);

    // Move it into the capsule and register a destructor that frees the memory
    let capsule = PyCapsule::new_with_destructor(
        py,
        ptr,
        None,
        |ptr, _| {
            // Reconstruct the Box and let it drop, freeing the allocation
            let _ = unsafe { Box::from_raw(ptr) };
        },
    )
    .expect("capsule creation failed");

    // ... pass `capsule` back to Python ...
});
```

**不要**使用 `PyCapsule::new(…, None)`；该变体*不会*注册析构器，除非接收方手动提取并释放指针（我们从不依赖这种行为），否则会发生内存泄漏。代码库已在所有位置遵循该规则——新添加的 FFI 模块也必须遵循相同模式。

## 为什么不再有通用的 `cvec_drop`

更早期的代码库提供过一个通用的 `cvec_drop` 函数，它总是将缓冲区视为 `Vec<u8>`。若用于任何其他元素类型，会在释放时出现大小不匹配，破坏分配器的内部账本。由于项目内部并未引用该辅助函数，已将其移除以避免误用。

请改用针对元素类型的**类型特定**释放辅助函数（如 `vec_drop_book_levels`、`vec_drop_book_orders`）。如果你的类型尚无对应的辅助函数，请按照 `crates/core/src/ffi/cvec.rs` 中的模式添加一个。

## Box 支撑的 `*_API` 包装器（拥有所有权的 Rust 对象）

当 Rust 核心需要把一个*复杂*值（例如 `OrderBook`、`SyntheticInstrument` 或 `TimeEventAccumulator`）交给外部代码时，它会使用 `Box::new` 在堆上分配该值，并返回一个 `repr(C)` 的小包装器，唯一的字段就是这个 `Box`。

```rust
#[repr(C)]
pub struct OrderBook_API(Box<OrderBook>);

#[unsafe(no_mangle)]
pub extern "C" fn orderbook_new(id: InstrumentId, book_type: BookType) -> OrderBook_API {
    OrderBook_API(Box::new(OrderBook::new(id, book_type)))
}

#[unsafe(no_mangle)]
pub extern "C" fn orderbook_drop(book: OrderBook_API) {
    drop(book); // frees the heap allocation
}
```

由此带来的内存安全要求是：

1. 每个构造器（`*_new`）**必须**在其旁边导出一个匹配的 `*_drop`。
2. 在堆分配前完成参数校验，以便快速失败并避免分配出无效对象。
3. *Python/Cython* 绑定必须保证 `*_drop` 恰好被调用一次。有两种做法：

    • **推荐用于新代码**：使用 `PyCapsule::new_with_destructor` 创建 `PyCapsule` 来包装指针，传入会调用 drop 辅助函数的析构器。

    • **遗留模式**（仅限 v1 Cython 模块）：在 Python 侧的 `__del__`/`__dealloc__` 中显式调用辅助函数：

      ```python
      cdef class OrderBook:
          cdef OrderBook_API _mem

          def __cinit__(self, ...):
              self._mem = orderbook_new(...)

          def __del__(self):
              if self._mem._0 != NULL:
                  orderbook_drop(self._mem)
      ```

无论采用哪种风格，请记住：**遗漏 drop 调用会泄漏整个结构**，而调用两次将导致双重释放并使程序崩溃。

新的 FFI 代码必须使用带析构器的 `PyCapsule` 并遵循该模板，才能被合并。
