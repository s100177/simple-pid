def _clamp(value, limits):
    lower, upper = limits
    if value is None:
        return None
    elif (upper is not None) and (value > upper):
        return upper
    elif (lower is not None) and (value < lower):
        return lower
    return value


class PID(object):
    """A simple PID controller."""

    def __init__(
        self,
        Kp=1.0,
        Ki=0.0,
        Kd=0.0,
        setpoint=0,
        sample_time=0.01,
        output_limits=(None, None),
        output_rate_limits=(None, None),
        auto_mode=True,
        proportional_on_measurement=False,
        differential_on_measurement=True,
        error_map=None,
        time_fn=None,
        starting_output=0.0,
    ):
        """
        初始化一个新的PID控制器。

        :param Kp: 比例增益Kp的值
        :param Ki: 积分增益Ki的值
        :param Kd: 微分增益Kd的值
        :param setpoint: PID控制器试图达到的初始设定值
        :param sample_time: 控制器在生成新输出值之前应等待的时间（秒）。PID在持续调用时（例如在循环中）
            效果最佳，但需要设置采样时间，使得每次更新之间的时间差（接近）恒定。如果设置为None，
            PID将在每次调用时计算新的输出值。
        :param output_limits: 要使用的初始输出限制，给定为一个包含2个元素的迭代对象，例如：(lower, upper)。
            输出永远不会低于下限或高于上限。任一限制也可以设置为None以在该方向上无限制。设置输出限制
            还可以避免积分饱和，因为积分项永远不会被允许在限制范围外增长。
        :param output_rate_limits: 要使用的输出变化率限制（变幅约束），给定为一个包含2个元素的迭代对象，
            例如：(lower_rate, upper_rate)。输出变化率永远不会低于下限变化率或高于上限变化率（每单位时间）。
            任一限制也可以设置为None以在该方向上无限制。这限制了输出可以变化的速度，对于无法处理控制信号
            快速变化的系统很有用。
        :param auto_mode: 控制器是否应启用（自动模式）或不启用（手动模式）
        :param proportional_on_measurement: 比例项是否应直接在输入上计算，而不是在误差上计算（传统方式）。
            使用基于测量的比例项可以避免某些类型系统的超调。
        :param differential_on_measurement: 微分项是否应直接在输入上计算，而不是在误差上计算（传统方式）。
        :param error_map: 用于将误差值转换为另一个约束值的函数。
        :param time_fn: 用于获取当前时间的函数，或None以使用默认值。这应该是一个不接受参数并返回表示
            当前时间的数字的函数。默认情况下，如果可用则使用time.monotonic()，否则使用time.time()。
        :param starting_output: PID输出的起始点。如果您开始控制一个已经处于设定值的系统，可以将其设置为
            您对PID首次调用时应给出的输出的最佳猜测，以避免PID输出零并将系统移离设定值。
        """
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.setpoint = setpoint
        self.sample_time = sample_time

        self._min_output, self._max_output = None, None
        self._min_output_rate, self._max_output_rate = None, None
        self._auto_mode = auto_mode
        self.proportional_on_measurement = proportional_on_measurement
        self.differential_on_measurement = differential_on_measurement
        self.error_map = error_map

        self._proportional = 0
        self._integral = 0
        self._derivative = 0

        self._last_time = None
        self._last_output = None
        self._last_error = None
        self._last_input = None

        if time_fn is not None:
            # Use the user supplied time function
            self.time_fn = time_fn
        else:
            import time

            try:
                # Get monotonic time to ensure that time deltas are always positive
                self.time_fn = time.monotonic
            except AttributeError:
                # time.monotonic() not available (using python < 3.3), fallback to time.time()
                self.time_fn = time.time

        self.output_limits = output_limits
        self.output_rate_limits = output_rate_limits
        self.reset()

        # Set initial state of the controller
        self._integral = _clamp(starting_output, output_limits)

    def __call__(self, input_, dt=None):
        """
        Update the PID controller.

        Call the PID controller with *input_* and calculate and return a control output if
        sample_time seconds has passed since the last update. If no new output is calculated,
        return the previous output instead (or None if no value has been calculated yet).

        :param dt: If set, uses this value for timestep instead of real time. This can be used in
            simulations when simulation time is different from real time.
        """
        if not self.auto_mode:
            return self._last_output

        now = self.time_fn()
        if dt is None:
            dt = now - self._last_time if (now - self._last_time) else 1e-16
        elif dt <= 0:
            raise ValueError('dt has negative value {}, must be positive'.format(dt))

        if self.sample_time is not None and dt < self.sample_time and self._last_output is not None:
            # Only update every sample_time seconds
            return self._last_output

        # Compute error terms
        error = self.setpoint - input_
        d_input = input_ - (self._last_input if (self._last_input is not None) else input_)
        d_error = error - (self._last_error if (self._last_error is not None) else error)

        # Check if must map the error
        if self.error_map is not None:
            error = self.error_map(error)

        # Compute the proportional term
        if not self.proportional_on_measurement:
            # Regular proportional-on-error, simply set the proportional term
            self._proportional = self.Kp * error
        else:
            # Add the proportional error on measurement to error_sum
            self._proportional -= self.Kp * d_input

        # Compute integral and derivative terms
        self._integral += self.Ki * error * dt
        self._integral = _clamp(self._integral, self.output_limits)  # Avoid integral windup

        if self.differential_on_measurement:
            self._derivative = -self.Kd * d_input / dt
        else:
            self._derivative = self.Kd * d_error / dt

        # Compute final output
        output = self._proportional + self._integral + self._derivative
        output = _clamp(output, self.output_limits)

        # Apply rate limits (变幅约束)
        if self._last_output is not None:
            output = self._apply_rate_limits(output, self._last_output, dt)

        # Keep track of state
        self._last_output = output
        self._last_input = input_
        self._last_error = error
        self._last_time = now

        return output

    def __repr__(self):
        return (
            '{self.__class__.__name__}('
            'Kp={self.Kp!r}, Ki={self.Ki!r}, Kd={self.Kd!r}, '
            'setpoint={self.setpoint!r}, sample_time={self.sample_time!r}, '
            'output_limits={self.output_limits!r}, output_rate_limits={self.output_rate_limits!r}, '
            'auto_mode={self.auto_mode!r}, '
            'proportional_on_measurement={self.proportional_on_measurement!r}, '
            'differential_on_measurement={self.differential_on_measurement!r}, '
            'error_map={self.error_map!r}'
            ')'
        ).format(self=self)

    @property
    def components(self):
        """
        The P-, I- and D-terms from the last computation as separate components as a tuple. Useful
        for visualizing what the controller is doing or when tuning hard-to-tune systems.
        """
        return self._proportional, self._integral, self._derivative

    @property
    def tunings(self):
        """The tunings used by the controller as a tuple: (Kp, Ki, Kd)."""
        return self.Kp, self.Ki, self.Kd

    @tunings.setter
    def tunings(self, tunings):
        """Set the PID tunings."""
        self.Kp, self.Ki, self.Kd = tunings

    @property
    def auto_mode(self):
        """Whether the controller is currently enabled (in auto mode) or not."""
        return self._auto_mode

    @auto_mode.setter
    def auto_mode(self, enabled):
        """Enable or disable the PID controller."""
        self.set_auto_mode(enabled)

    def set_auto_mode(self, enabled, last_output=None):
        """
        Enable or disable the PID controller, optionally setting the last output value.

        This is useful if some system has been manually controlled and if the PID should take over.
        In that case, disable the PID by setting auto mode to False and later when the PID should
        be turned back on, pass the last output variable (the control variable) and it will be set
        as the starting I-term when the PID is set to auto mode.

        :param enabled: Whether auto mode should be enabled, True or False
        :param last_output: The last output, or the control variable, that the PID should start
            from when going from manual mode to auto mode. Has no effect if the PID is already in
            auto mode.
        """
        if enabled and not self._auto_mode:
            # Switching from manual mode to auto, reset
            self.reset()

            self._integral = last_output if (last_output is not None) else 0
            self._integral = _clamp(self._integral, self.output_limits)

        self._auto_mode = enabled

    @property
    def output_limits(self):
        """
        The current output limits as a 2-tuple: (lower, upper).

        See also the *output_limits* parameter in :meth:`PID.__init__`.
        """
        return self._min_output, self._max_output

    @output_limits.setter
    def output_limits(self, limits):
        """Set the output limits."""
        if limits is None:
            self._min_output, self._max_output = None, None
            return

        min_output, max_output = limits

        if (None not in limits) and (max_output < min_output):
            raise ValueError('lower limit must be less than upper limit')

        self._min_output = min_output
        self._max_output = max_output

        self._integral = _clamp(self._integral, self.output_limits)
        self._last_output = _clamp(self._last_output, self.output_limits)

    def _apply_rate_limits(self, output, last_output, dt):
        """
        Apply rate limits to the output change (应用变幅约束).

        :param output: The desired output value
        :param last_output: The previous output value
        :param dt: The time step
        :return: The output value constrained by rate limits
        """
        if dt <= 0:
            return output

        desired_change = output - last_output
        max_change = None
        min_change = None

        if self._max_output_rate is not None:
            max_change = self._max_output_rate * dt
        if self._min_output_rate is not None:
            min_change = self._min_output_rate * dt

        if max_change is not None and desired_change > max_change:
            return last_output + max_change
        elif min_change is not None and desired_change < min_change:
            return last_output + min_change

        return output

    @property
    def output_rate_limits(self):
        """
        The current output rate limits as a 2-tuple: (lower_rate, upper_rate).

        See also the *output_rate_limits* parameter in :meth:`PID.__init__`.
        """
        return self._min_output_rate, self._max_output_rate

    @output_rate_limits.setter
    def output_rate_limits(self, limits):
        """Set the output rate limits."""
        if limits is None:
            self._min_output_rate, self._max_output_rate = None, None
            return

        min_rate, max_rate = limits

        if (None not in limits) and (max_rate < min_rate):
            raise ValueError('lower rate limit must be less than upper rate limit')

        self._min_output_rate = min_rate
        self._max_output_rate = max_rate

    def reset(self):
        """
        Reset the PID controller internals.

        This sets each term to 0 as well as clearing the integral, the last output and the last
        input (derivative calculation).
        """
        self._proportional = 0
        self._integral = 0
        self._derivative = 0

        self._integral = _clamp(self._integral, self.output_limits)

        self._last_time = self.time_fn()
        self._last_output = None
        self._last_input = None
        self._last_error = None
