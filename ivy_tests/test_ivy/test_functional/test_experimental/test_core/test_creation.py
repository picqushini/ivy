from hypothesis import strategies as st

# local
import ivy_tests.test_ivy.helpers as helpers
from ivy_tests.test_ivy.helpers import handle_test


@handle_test(
    fn_tree="functional.experimental.triu_indices",
    n_rows=helpers.ints(min_value=0, max_value=10),
    n_cols=st.none() | helpers.ints(min_value=0, max_value=10),
    k=helpers.ints(min_value=-10, max_value=10),
    test_instance_method=st.just(False),
)
def test_triu_indices(
    *,
    n_rows,
    n_cols,
    k,
    test_flags,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=["int32"],
        test_flags=test_flags,
        fw=backend_fw,
        on_device=on_device,
        fn_name=fn_name,
        n_rows=n_rows,
        n_cols=n_cols,
        k=k,
        device=on_device,
    )


# vorbis_window
@handle_test(
    fn_tree="functional.experimental.vorbis_window",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        min_num_dims=1,
        max_num_dims=1,
    ),
)
def test_vorbis_window(
    *,
    dtype_and_x,
    test_flags,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x = dtype_and_x
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        test_flags=test_flags,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        x=x[0],
        dtype=input_dtype[0],
    )


# hann_window
@handle_test(
    fn_tree="functional.experimental.hann_window",
    window_length=helpers.ints(min_value=1, max_value=10),
    input_dtype=helpers.get_dtypes("integer"),
    periodic=st.booleans(),
    dtype=helpers.get_dtypes("float", full=False),
)
def test_hann_window(
    *,
    window_length,
    input_dtype,
    periodic,
    dtype,
    test_flags,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        test_flags=test_flags,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        window_length=window_length,
        periodic=periodic,
        dtype=dtype,
    )


# kaiser_window
@handle_test(
    fn_tree="functional.experimental.kaiser_window",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("integer"),
        shape=(1, 1),
        min_value=1,
        max_value=10,
    ),
    periodic=st.booleans(),
    beta=st.floats(min_value=0, max_value=5),
    dtype=helpers.get_dtypes("float", full=False),
)
def test_kaiser_window(
    *,
    dtype_and_x,
    periodic,
    beta,
    dtype,
    test_flags,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x = dtype_and_x
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        test_flags=test_flags,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        window_length=x[0],
        periodic=periodic,
        beta=beta,
        dtype=dtype,
    )


# kaiser_bessel_derived_window
@handle_test(
    fn_tree="functional.experimental.kaiser_bessel_derived_window",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        shape=(1, 1),
        min_value=1,
        max_value=10,
    ),
    periodic=st.booleans(),
    beta=st.floats(min_value=1, max_value=5),
    dtype=helpers.get_dtypes("float"),
)
def test_kaiser_bessel_derived_window(
    *,
    dtype_and_x,
    periodic,
    beta,
    dtype,
    test_flags,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x = dtype_and_x
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        test_flags=test_flags,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        window_length=x[0],
        periodic=periodic,
        beta=beta,
        dtype=dtype,
    )


# hamming_window
@handle_test(
    fn_tree="functional.experimental.hamming_window",
    window_length=helpers.ints(min_value=1, max_value=10),
    input_dtype=helpers.get_dtypes("integer"),
    periodic=st.booleans(),
    alpha=st.floats(min_value=1, max_value=5),
    beta=st.floats(min_value=1, max_value=5),
    dtype=helpers.get_dtypes("float", full=False),
)
def test_hamming_window(
    *,
    window_length,
    input_dtype,
    periodic,
    alpha,
    beta,
    dtype,
    test_flags,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        test_flags=test_flags,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        window_length=window_length,
        periodic=periodic,
        alpha=alpha,
        beta=beta,
        dtype=dtype,
    )


@handle_test(
    fn_tree="functional.experimental.tril_indices",
    n_rows=helpers.ints(min_value=0, max_value=10),
    n_cols=st.none() | helpers.ints(min_value=0, max_value=10),
    k=helpers.ints(min_value=-11, max_value=11),
    dtypes=helpers.get_dtypes("integer"),
)
def test_tril_indices(
    *,
    n_rows,
    n_cols,
    k,
    dtypes,
    num_positional_args,
    as_variable,
    native_array,
    container_flags,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    helpers.test_function(
        input_dtypes=dtypes,
        ground_truth_backend=ground_truth_backend,
        as_variable_flags=as_variable,
        with_out=False,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=False,
        fw=backend_fw,
        on_device=on_device,
        fn_name=fn_name,
        n_rows=n_rows,
        n_cols=n_cols,
        k=k,
        device=on_device,
    )
