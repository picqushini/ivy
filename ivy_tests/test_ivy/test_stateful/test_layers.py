"""Collection of tests for unified neural network layers."""

# global
import numpy as np
from hypothesis import strategies as st, assume

# local
import ivy
from ivy.functional.ivy.gradients import _variable
from ivy.container import Container
import ivy_tests.test_ivy.helpers as helpers
import ivy.functional.backends.numpy as ivy_np
from ivy_tests.test_ivy.helpers.assertions import assert_same_type_and_shape
import ivy_tests.test_ivy.helpers.test_parameter_flags as pf
from ivy_tests.test_ivy.helpers import handle_method


# Helpers #
# --------#

all_constant_initializers = (ivy.Zeros, ivy.Ones)
all_uniform_initializers = (ivy.GlorotUniform, ivy.FirstLayerSiren, ivy.Siren)
all_gaussian_initializers = (ivy.KaimingNormal, ivy.Siren)
all_initializers = (
    all_constant_initializers + all_uniform_initializers + all_gaussian_initializers
)


@st.composite
def _sample_initializer(draw):
    return draw(st.sampled_from(all_initializers))()


# Linear #
# -------#


@st.composite
def _bias_flag_and_initializer(draw):
    with_bias = draw(st.booleans())
    if with_bias:
        return with_bias, draw(_sample_initializer())
    return with_bias, None


@st.composite
def _input_channels_and_dtype_and_values(draw):
    input_channels = draw(st.integers(min_value=1, max_value=2))
    x_shape = draw(helpers.get_shape()) + (input_channels,)
    dtype, vals = draw(
        helpers.dtype_and_values(
            available_dtypes=helpers.get_dtypes("float"),
            shape=x_shape,
            min_value=0,
            max_value=1,
            small_abs_safety_factor=4,
            safety_factor_scale="log",
        )
    )
    return input_channels, dtype, vals


# linear
@handle_method(
    method_tree="Linear.__call__",
    ic_n_dtype_n_vals=_input_channels_and_dtype_and_values(),
    output_channels=st.shared(
        st.integers(min_value=1, max_value=2), key="output_channels"
    ),
    weight_initializer=_sample_initializer(),
    wb_n_b_init=_bias_flag_and_initializer(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
    seed=helpers.seed(),
)
def test_linear_layer(
    *,
    ic_n_dtype_n_vals,
    output_channels,
    weight_initializer,
    wb_n_b_init,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    seed,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    ivy.seed(seed_value=seed)
    input_channels, input_dtype, x = ic_n_dtype_n_vals
    with_bias, bias_initializer = wb_n_b_init
    helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "input_channels": input_channels,
            "output_channels": output_channels,
            "weight_initializer": weight_initializer,
            "bias_initializer": bias_initializer,
            "with_bias": with_bias,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=method_container_flags,
        method_all_as_kwargs_np={"x": x[0]},
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-02,
        atol_=1e-02,
    )


# Dropout #
# --------#

# dropout
@handle_method(
    method_tree="Dropout.__call__",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        min_value=0,
        max_value=50,
        allow_inf=False,
        min_num_dims=1,
        max_num_dims=1,
        min_dim_size=2,
    ),
    prob=helpers.floats(min_value=0, max_value=0.9),
    scale=st.booleans(),
)
def test_dropout_layer(
    *,
    dtype_and_x,
    prob,
    scale,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    input_dtype, x = dtype_and_x
    ret = helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "prob": prob,
            "scale": scale,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=method_container_flags,
        method_all_as_kwargs_np={"inputs": x[0]},
        class_name=class_name,
        method_name=method_name,
        test_values=False,
    )
    ret = helpers.flatten_and_to_np(ret=ret)
    for u in ret:
        # cardinality test
        assert u.shape == x[0].shape


# Attention #
# ----------#
@st.composite
def x_and_mha(draw):
    dtype = draw(
        helpers.get_dtypes("float", full=False).filter(lambda x: x != ["float16"])
    )
    with_to_q_fn = draw(st.booleans())
    with_to_kv_fn = draw(st.booleans())
    with_to_out_fn = draw(st.booleans())
    query_dim = draw(st.integers(min_value=1, max_value=3))
    num_heads = draw(st.integers(min_value=1, max_value=3))
    head_dim = draw(st.integers(min_value=1, max_value=3))
    dropout_rate = draw(st.floats(min_value=0.0, max_value=0.9))
    context_dim = draw(st.integers(min_value=1, max_value=3))
    scale = draw(st.integers(min_value=1, max_value=3))

    num_queries = draw(st.integers(min_value=1, max_value=3))
    # x_feats = draw(st.integers(min_value=1, max_value=3))
    # cont_feats = draw(st.integers(min_value=1, max_value=3))
    num_keys = draw(st.integers(min_value=1, max_value=3))
    if with_to_q_fn:
        inputs_shape = (num_queries, query_dim)
    else:
        inputs_shape = (num_queries, num_heads * head_dim)
    if with_to_kv_fn:
        context_shape = (num_keys, context_dim)
    else:
        context_shape = (num_keys, num_heads * head_dim * 2)
    mask_shape = (num_queries, num_keys)
    x_mha = draw(
        helpers.array_values(
            dtype=dtype[0],
            shape=inputs_shape,
            min_value=0.0999755859375,
            max_value=1,
        )
    )
    context = draw(
        helpers.array_values(
            dtype=dtype[0],
            shape=context_shape,
            min_value=0.0999755859375,
            max_value=1,
        )
    )
    mask = draw(
        helpers.array_values(
            dtype=dtype[0],
            shape=mask_shape,
            min_value=0.0999755859375,
            max_value=1,
        )
    )
    return (
        dtype,
        x_mha,
        scale,
        num_heads,
        context,
        mask,
        query_dim,
        head_dim,
        dropout_rate,
        context_dim,
        with_to_q_fn,
        with_to_kv_fn,
        with_to_out_fn,
    )


# multi_head_attention
@handle_method(
    method_tree="MultiHeadAttention.__call__",
    dtype_mha=x_and_mha(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
    num_positional_args_method=helpers.num_positional_args(
        fn_name="MultiHeadAttention._forward"
    ),
    build_mode=st.just("on_init"),
)
def test_multi_head_attention_layer(
    dtype_mha,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    build_mode,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    (
        input_dtype,
        x_mha,
        scale,
        num_heads,
        context,
        mask,
        query_dim,
        head_dim,
        dropout_rate,
        context_dim,
        with_to_q_fn,
        with_to_kv_fn,
        with_to_out_fn,
    ) = dtype_mha
    ret_np_flat, ret_np_from_gt_flat = helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "query_dim": query_dim,
            "num_heads": num_heads,
            "head_dim": head_dim,
            "dropout_rate": dropout_rate,
            "context_dim": context_dim,
            "with_to_q_fn": with_to_q_fn,
            "with_to_kv_fn": with_to_kv_fn,
            "with_to_out_fn": with_to_out_fn,
            "build_mode": build_mode,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=method_container_flags,
        method_all_as_kwargs_np={
            "inputs": np.asarray(x_mha, dtype=input_dtype[0]),
            "context": np.asarray(context, dtype=input_dtype[0]),
            "mask": np.asarray(mask, dtype=input_dtype[0]),
        },
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-2,
        atol_=1e-2,
        test_values=False,
        return_flat_np_arrays=True,
    )
    assert_same_type_and_shape([ret_np_flat, ret_np_from_gt_flat])


# Convolutions #
# -------------#


@st.composite
def _x_ic_oc_f_d_df(draw, dim: int = 2, transpose: bool = False, depthwise=False):
    strides = draw(st.integers(min_value=1, max_value=3))
    padding = draw(st.sampled_from(["SAME", "VALID"]))
    batch_size = draw(st.integers(1, 1))
    filter_shape = draw(
        helpers.get_shape(
            min_num_dims=dim, max_num_dims=dim, min_dim_size=1, max_dim_size=5
        )
    )
    input_channels = draw(st.integers(1, 3))
    output_channels = draw(st.integers(1, 3))
    dilations = draw(st.integers(1, 2))
    x_dim = []
    for i in range(dim):
        min_x = filter_shape[i] + (filter_shape[i] - 1) * (dilations - 1)
        x_dim.append(draw(st.integers(min_x, 20)))
    if dim == 2:
        data_format = draw(st.sampled_from(["NCHW"]))
    elif dim == 1:
        data_format = draw(st.sampled_from(["NWC", "NCW"]))
    else:
        data_format = draw(st.sampled_from(["NDHWC", "NCDHW"]))
    if data_format == "NHWC" or data_format == "NWC" or data_format == "NDHWC":
        x_shape = [batch_size] + x_dim + [input_channels]
    else:
        x_shape = [batch_size] + [input_channels] + x_dim

    if transpose:
        output_shape = []
        for i in range(dim):
            output_shape.append(
                ivy.deconv_length(
                    x_dim[i], strides, filter_shape[i], padding, dilations
                )
            )
    filter_shape = list(filter_shape)
    if dim == 1:
        filter_shape = filter_shape[0]
    dtype, vals = draw(
        helpers.dtype_and_values(
            available_dtypes=helpers.get_dtypes("float", full=True),
            shape=x_shape,
            min_value=0,
            max_value=1,
        ).filter(lambda x: x[0] != ["float16"])
    )
    if transpose:
        return (
            dtype,
            vals,
            input_channels,
            output_channels,
            filter_shape,
            strides,
            dilations,
            data_format,
            padding,
            output_shape,
        )
    return (
        dtype,
        vals,
        input_channels,
        output_channels,
        filter_shape,
        strides,
        dilations,
        data_format,
        padding,
    )


# conv1d
@handle_method(
    method_tree="Conv1D.__call__",
    _x_ic_oc_f_s_d_df_p=_x_ic_oc_f_d_df(dim=1),
    weight_initializer=_sample_initializer(),
    bias_initializer=_sample_initializer(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
)
def test_conv1d_layer(
    _x_ic_oc_f_s_d_df_p,
    weight_initializer,
    bias_initializer,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    (
        input_dtype,
        vals,
        input_channels,
        output_channels,
        filter_shape,
        strides,
        dilations,
        data_format,
        padding,
    ) = _x_ic_oc_f_s_d_df_p
    helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "input_channels": input_channels,
            "output_channels": output_channels,
            "filter_shape": filter_shape,
            "strides": strides,
            "padding": padding,
            "weight_initializer": weight_initializer,
            "bias_initializer": bias_initializer,
            "data_format": data_format,
            "dilations": dilations,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=False,
        method_all_as_kwargs_np={"inputs": vals[0]},
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-02,
        atol_=1e-02,
    )


# conv1d transpose
@handle_method(
    method_tree="Conv1DTranspose.__call__",
    ground_truth_backend="jax",
    _x_ic_oc_f_s_d_df_p=_x_ic_oc_f_d_df(dim=1, transpose=True),
    weight_initializer=_sample_initializer(),
    bias_initializer=_sample_initializer(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
    num_positional_args_method=helpers.num_positional_args(
        fn_name="Conv1DTranspose._forward"
    ),
)
def test_conv1d_transpose_layer(
    _x_ic_oc_f_s_d_df_p,
    weight_initializer,
    bias_initializer,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    (
        input_dtype,
        vals,
        input_channels,
        output_channels,
        filter_shape,
        strides,
        dilations,
        data_format,
        padding,
        output_shape,
    ) = _x_ic_oc_f_s_d_df_p
    assume(
        not (
            ivy.current_backend_str() == "tensorflow"
            and on_device == "cpu"
            and dilations > 1
        )
    )
    helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "input_channels": input_channels,
            "output_channels": output_channels,
            "filter_shape": filter_shape,
            "strides": strides,
            "padding": padding,
            "weight_initializer": weight_initializer,
            "bias_initializer": bias_initializer,
            "output_shape": output_shape,
            "data_format": data_format,
            "dilations": dilations,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=False,
        method_all_as_kwargs_np={"inputs": vals[0]},
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-02,
        atol_=1e-02,
    )


# # conv2d
@handle_method(
    method_tree="Conv2D.__call__",
    _x_ic_oc_f_s_d_df_p=_x_ic_oc_f_d_df(),
    weight_initializer=_sample_initializer(),
    bias_initializer=_sample_initializer(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
)
def test_conv2d_layer(
    _x_ic_oc_f_s_d_df_p,
    weight_initializer,
    bias_initializer,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    (
        input_dtype,
        vals,
        input_channels,
        output_channels,
        filter_shape,
        strides,
        dilations,
        data_format,
        padding,
    ) = _x_ic_oc_f_s_d_df_p
    helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "input_channels": input_channels,
            "output_channels": output_channels,
            "filter_shape": filter_shape,
            "strides": strides,
            "padding": padding,
            "weight_initializer": weight_initializer,
            "bias_initializer": bias_initializer,
            "data_format": data_format,
            "dilations": dilations,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=method_container_flags,
        method_all_as_kwargs_np={"inputs": vals[0]},
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-02,
        atol_=1e-02,
    )


# # conv2d transpose
@handle_method(
    method_tree="Conv2DTranspose.__call__",
    ground_truth_backend="jax",
    _x_ic_oc_f_s_d_df_p=_x_ic_oc_f_d_df(transpose=True),
    weight_initializer=_sample_initializer(),
    bias_initializer=_sample_initializer(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
    num_positional_args_init=helpers.num_positional_args(
        fn_name="Conv2DTranspose.__init__"
    ),
    num_positional_args_method=helpers.num_positional_args(
        fn_name="Conv2DTranspose._forward"
    ),
)
def test_conv2d_transpose_layer(
    _x_ic_oc_f_s_d_df_p,
    weight_initializer,
    bias_initializer,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    (
        input_dtype,
        vals,
        input_channels,
        output_channels,
        filter_shape,
        strides,
        dilations,
        data_format,
        padding,
        output_shape,
    ) = _x_ic_oc_f_s_d_df_p
    assume(
        not (
            ivy.current_backend_str() == "tensorflow"
            and on_device == "cpu"
            and dilations > 1
        )
    )
    helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "input_channels": input_channels,
            "output_channels": output_channels,
            "filter_shape": filter_shape,
            "strides": strides,
            "padding": padding,
            "weight_initializer": weight_initializer,
            "bias_initializer": bias_initializer,
            "output_shape": output_shape,
            "data_format": data_format,
            "dilations": dilations,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=method_container_flags,
        method_all_as_kwargs_np={"inputs": vals[0]},
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-02,
        atol_=1e-02,
    )


# # depthwise conv2d
@handle_method(
    method_tree="DepthwiseConv2D.__call__",
    ground_truth_backend="jax",
    _x_ic_oc_f_s_d_df_p=_x_ic_oc_f_d_df(depthwise=True),
    weight_initializer=_sample_initializer(),
    bias_initializer=_sample_initializer(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
    num_positional_args_method=helpers.num_positional_args(
        fn_name="DepthwiseConv2D._forward"
    ),
)
def test_depthwise_conv2d_layer(
    _x_ic_oc_f_s_d_df_p,
    weight_initializer,
    bias_initializer,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    (
        input_dtype,
        vals,
        input_channels,
        output_channels,
        filter_shape,
        strides,
        dilations,
        data_format,
        padding,
    ) = _x_ic_oc_f_s_d_df_p
    assume(
        not (
            ivy.current_backend_str() == "tensorflow" and dilations > 1 and strides > 1
        )
    )
    helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "num_channels": input_channels,
            "filter_shape": filter_shape,
            "strides": strides,
            "padding": padding,
            "weight_initializer": weight_initializer,
            "bias_initializer": bias_initializer,
            "data_format": data_format,
            "dilations": dilations,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=method_container_flags,
        method_all_as_kwargs_np={"inputs": vals[0]},
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-02,
        atol_=1e-02,
    )


# conv3d
@handle_method(
    method_tree="Conv3D.__call__",
    ground_truth_backend="jax",
    _x_ic_oc_f_s_d_df_p=_x_ic_oc_f_d_df(dim=3),
    weight_initializer=_sample_initializer(),
    bias_initializer=_sample_initializer(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
)
def test_conv3d_layer(
    _x_ic_oc_f_s_d_df_p,
    weight_initializer,
    bias_initializer,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    (
        input_dtype,
        vals,
        input_channels,
        output_channels,
        filter_shape,
        strides,
        dilations,
        data_format,
        padding,
    ) = _x_ic_oc_f_s_d_df_p
    helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "input_channels": input_channels,
            "output_channels": output_channels,
            "filter_shape": filter_shape,
            "strides": strides,
            "padding": padding,
            "weight_initializer": weight_initializer,
            "bias_initializer": bias_initializer,
            "data_format": data_format,
            "dilations": dilations,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=method_container_flags,
        method_all_as_kwargs_np={"inputs": vals[0]},
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-02,
        atol_=1e-02,
    )


# conv3d transpose
@handle_method(
    method_tree="Conv3DTranspose.__call__",
    ground_truth_backend="jax",
    _x_ic_oc_f_s_d_df_p=_x_ic_oc_f_d_df(dim=3, transpose=True),
    weight_initializer=_sample_initializer(),
    bias_initializer=_sample_initializer(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
    num_positional_args_init=helpers.num_positional_args(
        fn_name="Conv3DTranspose.__init__"
    ),
    num_positional_args_method=helpers.num_positional_args(
        fn_name="Conv3DTranspose._forward"
    ),
)
def test_conv3d_transpose_layer(
    _x_ic_oc_f_s_d_df_p,
    weight_initializer,
    bias_initializer,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    (
        input_dtype,
        vals,
        input_channels,
        output_channels,
        filter_shape,
        strides,
        dilations,
        data_format,
        padding,
        output_shape,
    ) = _x_ic_oc_f_s_d_df_p
    assume(
        not (
            ivy.current_backend_str() == "tensorflow"
            and on_device == "cpu"
            and dilations > 1
        )
    )
    helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "input_channels": input_channels,
            "output_channels": output_channels,
            "filter_shape": filter_shape,
            "strides": strides,
            "padding": padding,
            "weight_initializer": weight_initializer,
            "bias_initializer": bias_initializer,
            "output_shape": output_shape,
            "data_format": data_format,
            "dilations": dilations,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=method_container_flags,
        method_all_as_kwargs_np={"inputs": vals[0]},
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-02,
        atol_=1e-02,
    )


# LSTM
@st.composite
def _input_channels_and_dtype_and_values_lstm(draw):
    input_channels = draw(st.integers(min_value=1, max_value=10))
    t = draw(st.integers(min_value=1, max_value=3))
    x_shape = draw(helpers.get_shape()) + (t, input_channels)
    dtype, vals = draw(
        helpers.dtype_and_values(
            available_dtypes=helpers.get_dtypes("float", full=True), shape=x_shape
        )
    )
    return input_channels, dtype, vals


@handle_method(
    method_tree="LSTM.__call__",
    input_dtype_val=_input_channels_and_dtype_and_values_lstm(),
    output_channels=st.shared(
        st.integers(min_value=1, max_value=10), key="output_channels"
    ),
    weight_initializer=_sample_initializer(),
    num_layers=st.integers(min_value=1, max_value=3),
    return_sequence=st.booleans(),
    return_state=st.booleans(),
    init_with_v=st.booleans(),
    method_with_v=st.booleans(),
)
def test_lstm_layer(
    input_dtype_val,
    output_channels,
    weight_initializer,
    num_layers,
    return_sequence,
    return_state,
    init_with_v,
    method_with_v,
    num_positional_args_init: pf.NumPositionalArg,
    num_positional_args_method: pf.NumPositionalArg,
    method_as_variable_flags: pf.AsVariableFlags,
    method_native_array_flags: pf.NativeArrayFlags,
    method_container_flags: pf.ContainerFlags,
    on_device,
    class_name,
    method_name,
    ground_truth_backend,
):
    input_channels, input_dtype, vals = input_dtype_val
    return_sequence = return_sequence
    return_state = return_state
    helpers.test_method(
        ground_truth_backend=ground_truth_backend,
        init_num_positional_args=num_positional_args_init,
        init_all_as_kwargs_np={
            "input_channels": input_channels,
            "output_channels": output_channels,
            "weight_initializer": weight_initializer,
            "num_layers": num_layers,
            "return_sequence": return_sequence,
            "return_state": return_state,
            "device": on_device,
            "dtype": input_dtype[0],
        },
        method_input_dtypes=input_dtype,
        method_as_variable_flags=method_as_variable_flags,
        method_num_positional_args=num_positional_args_method,
        method_native_array_flags=method_native_array_flags,
        method_container_flags=method_container_flags,
        method_all_as_kwargs_np={"inputs": np.asarray(vals[0], dtype=input_dtype[0])},
        class_name=class_name,
        method_name=method_name,
        init_with_v=init_with_v,
        method_with_v=method_with_v,
        rtol_=1e-01,
        atol_=1e-01,
    )


# # Sequential #
@handle_method(
    method_tree="Sequential.__call__",
    bs_c_target=st.sampled_from(
        [
            (
                [1, 2],
                5,
                [
                    [
                        [-0.34784955, 0.47909835, 0.7241975, -0.82175905, -0.43836743],
                        [-0.34784955, 0.47909835, 0.7241975, -0.82175905, -0.43836743],
                    ]
                ],
            )
        ]
    ),
    with_v=st.booleans(),
    seq_v=st.booleans(),
    dtype=st.sampled_from(list(ivy_np.valid_float_dtypes) + [None]),
    method_as_variable_flags=st.booleans(),
)
def test_sequential_layer(
    bs_c_target,
    with_v,
    seq_v,
    dtype,
    method_as_variable_flags,
    on_device,
    compile_graph,
    method_name,
    class_name,
):
    # smoke test
    batch_shape, channels, target = bs_c_target
    tolerance_dict = {"float16": 1e-2, "float32": 1e-5, "float64": 1e-5, None: 1e-5}
    if method_as_variable_flags:
        x = _variable(
            ivy.asarray(
                ivy.linspace(ivy.zeros(batch_shape), ivy.ones(batch_shape), channels),
                dtype=dtype,
            )
        )
    else:
        x = ivy.asarray(
            ivy.linspace(ivy.zeros(batch_shape), ivy.ones(batch_shape), channels),
            dtype=dtype,
        )
    if with_v:
        np.random.seed(0)
        wlim = (6 / (channels + channels)) ** 0.5
        v = Container(
            {
                "submodules": {
                    "v0": {
                        "w": _variable(
                            ivy.array(
                                np.random.uniform(-wlim, wlim, (channels, channels)),
                                dtype=dtype,
                                device=on_device,
                            )
                        ),
                        "b": _variable(
                            ivy.zeros([channels], device=on_device, dtype=dtype)
                        ),
                    },
                    "v2": {
                        "w": _variable(
                            ivy.array(
                                np.random.uniform(-wlim, wlim, (channels, channels)),
                                dtype=dtype,
                                device=on_device,
                            )
                        ),
                        "b": _variable(
                            ivy.zeros([channels], device=on_device, dtype=dtype)
                        ),
                    },
                }
            }
        )
    else:
        v = None
    if seq_v:
        seq = ivy.Sequential(
            ivy.Linear(channels, channels, device=on_device, dtype=dtype),
            ivy.Dropout(0.0),
            ivy.Linear(channels, channels, device=on_device, dtype=dtype),
            device=on_device,
            v=v if with_v else None,
            dtype=dtype,
        )
    else:
        seq = ivy.Sequential(
            ivy.Linear(
                channels,
                channels,
                device=on_device,
                v=v["submodules"]["v0"] if with_v else None,
                dtype=dtype,
            ),
            ivy.Dropout(0.0),
            ivy.Linear(
                channels,
                channels,
                device=on_device,
                v=v["submodules"]["v2"] if with_v else None,
                dtype=dtype,
            ),
            device=on_device,
        )
    ret = seq(x)
    # type test
    assert ivy.is_ivy_array(ret)
    # cardinality test
    assert ret.shape == tuple(batch_shape + [channels])
    # value test
    if not with_v:
        return
    assert np.allclose(
        ivy.to_numpy(seq(x)), np.array(target), rtol=tolerance_dict[dtype]
    )
