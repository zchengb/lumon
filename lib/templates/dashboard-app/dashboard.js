import { i as e, n as t, t as n } from "./rolldown-runtime-Dbv0sNQl.js";
import { t as r } from "./chunk-KS23V3DP-BLgekSrB.js";
import { _ as i, g as a, h as o, p as s } from "./src-B53NoQT1.js";
import { J as c, M as l, P as u, R as d, S as f, V as p, W as m, X as h, Y as g, c as _, f as v, g as y, h as b, j as x, l as S, n as C, p as w, q as T, r as E, t as D, w as O, x as k, y as ee } from "./chunk-ABZYJK2D-CVevQ3ur.js";
import { a as A, d as j, h as M, i as N, m as P, r as te } from "./chunk-S3R3BYOJ-BtVK2Rr4.js";
import { t as ne } from "./chunk-EXTU4WIE-By1ZThX0.js";
import { n as re, t as ie } from "./chunk-MI3HLSF2-DVisFF9Y.js";
import "./chunk-HN2XXSSU-BzJE2DVW.js";
import "./chunk-CVBHYZKI-utcCkCdu.js";
import "./chunk-ATLVNIR6-CY_EFS1R.js";
import { i as F, s as ae } from "./chunk-JA3XYJ7Z-RwfPEVEr.js";
import "./chunk-JZLCHNYA-Ci7qRJgj.js";
import "./chunk-QXUST7PY-DUpJQbC-.js";
import { n as oe } from "./chunk-N4CR4FBY-C3Oe3dWX.js";
import { t as se } from "./isEmpty-DbxQP0Mx.js";
//#region node_modules/react/cjs/react.production.js
var ce = /* @__PURE__ */ n(((e) => {
	var t = Symbol.for("react.transitional.element"), n = Symbol.for("react.portal"), r = Symbol.for("react.fragment"), i = Symbol.for("react.strict_mode"), a = Symbol.for("react.profiler"), o = Symbol.for("react.consumer"), s = Symbol.for("react.context"), c = Symbol.for("react.forward_ref"), l = Symbol.for("react.suspense"), u = Symbol.for("react.memo"), d = Symbol.for("react.lazy"), f = Symbol.for("react.activity"), p = Symbol.iterator;
	function m(e) {
		return typeof e != "object" || !e ? null : (e = p && e[p] || e["@@iterator"], typeof e == "function" ? e : null);
	}
	var h = {
		isMounted: function() {
			return !1;
		},
		enqueueForceUpdate: function() {},
		enqueueReplaceState: function() {},
		enqueueSetState: function() {}
	}, g = Object.assign, _ = {};
	function v(e, t, n) {
		this.props = e, this.context = t, this.refs = _, this.updater = n || h;
	}
	v.prototype.isReactComponent = {}, v.prototype.setState = function(e, t) {
		if (typeof e != "object" && typeof e != "function" && e != null) throw Error("takes an object of state variables to update or a function which returns an object of state variables.");
		this.updater.enqueueSetState(this, e, t, "setState");
	}, v.prototype.forceUpdate = function(e) {
		this.updater.enqueueForceUpdate(this, e, "forceUpdate");
	};
	function y() {}
	y.prototype = v.prototype;
	function b(e, t, n) {
		this.props = e, this.context = t, this.refs = _, this.updater = n || h;
	}
	var x = b.prototype = new y();
	x.constructor = b, g(x, v.prototype), x.isPureReactComponent = !0;
	var S = Array.isArray;
	function C() {}
	var w = {
		H: null,
		A: null,
		T: null,
		S: null
	}, T = Object.prototype.hasOwnProperty;
	function E(e, n, r) {
		var i = r.ref;
		return {
			$$typeof: t,
			type: e,
			key: n,
			ref: i === void 0 ? null : i,
			props: r
		};
	}
	function D(e, t) {
		return E(e.type, t, e.props);
	}
	function O(e) {
		return typeof e == "object" && !!e && e.$$typeof === t;
	}
	function k(e) {
		var t = {
			"=": "=0",
			":": "=2"
		};
		return "$" + e.replace(/[=:]/g, function(e) {
			return t[e];
		});
	}
	var ee = /\/+/g;
	function A(e, t) {
		return typeof e == "object" && e && e.key != null ? k("" + e.key) : t.toString(36);
	}
	function j(e) {
		switch (e.status) {
			case "fulfilled": return e.value;
			case "rejected": throw e.reason;
			default: switch (typeof e.status == "string" ? e.then(C, C) : (e.status = "pending", e.then(function(t) {
				e.status === "pending" && (e.status = "fulfilled", e.value = t);
			}, function(t) {
				e.status === "pending" && (e.status = "rejected", e.reason = t);
			})), e.status) {
				case "fulfilled": return e.value;
				case "rejected": throw e.reason;
			}
		}
		throw e;
	}
	function M(e, r, i, a, o) {
		var s = typeof e;
		(s === "undefined" || s === "boolean") && (e = null);
		var c = !1;
		if (e === null) c = !0;
		else switch (s) {
			case "bigint":
			case "string":
			case "number":
				c = !0;
				break;
			case "object": switch (e.$$typeof) {
				case t:
				case n:
					c = !0;
					break;
				case d: return c = e._init, M(c(e._payload), r, i, a, o);
			}
		}
		if (c) return o = o(e), c = a === "" ? "." + A(e, 0) : a, S(o) ? (i = "", c != null && (i = c.replace(ee, "$&/") + "/"), M(o, r, i, "", function(e) {
			return e;
		})) : o != null && (O(o) && (o = D(o, i + (o.key == null || e && e.key === o.key ? "" : ("" + o.key).replace(ee, "$&/") + "/") + c)), r.push(o)), 1;
		c = 0;
		var l = a === "" ? "." : a + ":";
		if (S(e)) for (var u = 0; u < e.length; u++) a = e[u], s = l + A(a, u), c += M(a, r, i, s, o);
		else if (u = m(e), typeof u == "function") for (e = u.call(e), u = 0; !(a = e.next()).done;) a = a.value, s = l + A(a, u++), c += M(a, r, i, s, o);
		else if (s === "object") {
			if (typeof e.then == "function") return M(j(e), r, i, a, o);
			throw r = String(e), Error("Objects are not valid as a React child (found: " + (r === "[object Object]" ? "object with keys {" + Object.keys(e).join(", ") + "}" : r) + "). If you meant to render a collection of children, use an array instead.");
		}
		return c;
	}
	function N(e, t, n) {
		if (e == null) return e;
		var r = [], i = 0;
		return M(e, r, "", "", function(e) {
			return t.call(n, e, i++);
		}), r;
	}
	function P(e) {
		if (e._status === -1) {
			var t = e._result;
			t = t(), t.then(function(t) {
				(e._status === 0 || e._status === -1) && (e._status = 1, e._result = t);
			}, function(t) {
				(e._status === 0 || e._status === -1) && (e._status = 2, e._result = t);
			}), e._status === -1 && (e._status = 0, e._result = t);
		}
		if (e._status === 1) return e._result.default;
		throw e._result;
	}
	var te = typeof reportError == "function" ? reportError : function(e) {
		if (typeof window == "object" && typeof window.ErrorEvent == "function") {
			var t = new window.ErrorEvent("error", {
				bubbles: !0,
				cancelable: !0,
				message: typeof e == "object" && e && typeof e.message == "string" ? String(e.message) : String(e),
				error: e
			});
			if (!window.dispatchEvent(t)) return;
		} else if (typeof process == "object" && typeof process.emit == "function") {
			process.emit("uncaughtException", e);
			return;
		}
		console.error(e);
	}, ne = {
		map: N,
		forEach: function(e, t, n) {
			N(e, function() {
				t.apply(this, arguments);
			}, n);
		},
		count: function(e) {
			var t = 0;
			return N(e, function() {
				t++;
			}), t;
		},
		toArray: function(e) {
			return N(e, function(e) {
				return e;
			}) || [];
		},
		only: function(e) {
			if (!O(e)) throw Error("React.Children.only expected to receive a single React element child.");
			return e;
		}
	};
	e.Activity = f, e.Children = ne, e.Component = v, e.Fragment = r, e.Profiler = a, e.PureComponent = b, e.StrictMode = i, e.Suspense = l, e.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE = w, e.__COMPILER_RUNTIME = {
		__proto__: null,
		c: function(e) {
			return w.H.useMemoCache(e);
		}
	}, e.cache = function(e) {
		return function() {
			return e.apply(null, arguments);
		};
	}, e.cacheSignal = function() {
		return null;
	}, e.cloneElement = function(e, t, n) {
		if (e == null) throw Error("The argument must be a React element, but you passed " + e + ".");
		var r = g({}, e.props), i = e.key;
		if (t != null) for (a in t.key !== void 0 && (i = "" + t.key), t) !T.call(t, a) || a === "key" || a === "__self" || a === "__source" || a === "ref" && t.ref === void 0 || (r[a] = t[a]);
		var a = arguments.length - 2;
		if (a === 1) r.children = n;
		else if (1 < a) {
			for (var o = Array(a), s = 0; s < a; s++) o[s] = arguments[s + 2];
			r.children = o;
		}
		return E(e.type, i, r);
	}, e.createContext = function(e) {
		return e = {
			$$typeof: s,
			_currentValue: e,
			_currentValue2: e,
			_threadCount: 0,
			Provider: null,
			Consumer: null
		}, e.Provider = e, e.Consumer = {
			$$typeof: o,
			_context: e
		}, e;
	}, e.createElement = function(e, t, n) {
		var r, i = {}, a = null;
		if (t != null) for (r in t.key !== void 0 && (a = "" + t.key), t) T.call(t, r) && r !== "key" && r !== "__self" && r !== "__source" && (i[r] = t[r]);
		var o = arguments.length - 2;
		if (o === 1) i.children = n;
		else if (1 < o) {
			for (var s = Array(o), c = 0; c < o; c++) s[c] = arguments[c + 2];
			i.children = s;
		}
		if (e && e.defaultProps) for (r in o = e.defaultProps, o) i[r] === void 0 && (i[r] = o[r]);
		return E(e, a, i);
	}, e.createRef = function() {
		return { current: null };
	}, e.forwardRef = function(e) {
		return {
			$$typeof: c,
			render: e
		};
	}, e.isValidElement = O, e.lazy = function(e) {
		return {
			$$typeof: d,
			_payload: {
				_status: -1,
				_result: e
			},
			_init: P
		};
	}, e.memo = function(e, t) {
		return {
			$$typeof: u,
			type: e,
			compare: t === void 0 ? null : t
		};
	}, e.startTransition = function(e) {
		var t = w.T, n = {};
		w.T = n;
		try {
			var r = e(), i = w.S;
			i !== null && i(n, r), typeof r == "object" && r && typeof r.then == "function" && r.then(C, te);
		} catch (e) {
			te(e);
		} finally {
			t !== null && n.types !== null && (t.types = n.types), w.T = t;
		}
	}, e.unstable_useCacheRefresh = function() {
		return w.H.useCacheRefresh();
	}, e.use = function(e) {
		return w.H.use(e);
	}, e.useActionState = function(e, t, n) {
		return w.H.useActionState(e, t, n);
	}, e.useCallback = function(e, t) {
		return w.H.useCallback(e, t);
	}, e.useContext = function(e) {
		return w.H.useContext(e);
	}, e.useDebugValue = function() {}, e.useDeferredValue = function(e, t) {
		return w.H.useDeferredValue(e, t);
	}, e.useEffect = function(e, t) {
		return w.H.useEffect(e, t);
	}, e.useEffectEvent = function(e) {
		return w.H.useEffectEvent(e);
	}, e.useId = function() {
		return w.H.useId();
	}, e.useImperativeHandle = function(e, t, n) {
		return w.H.useImperativeHandle(e, t, n);
	}, e.useInsertionEffect = function(e, t) {
		return w.H.useInsertionEffect(e, t);
	}, e.useLayoutEffect = function(e, t) {
		return w.H.useLayoutEffect(e, t);
	}, e.useMemo = function(e, t) {
		return w.H.useMemo(e, t);
	}, e.useOptimistic = function(e, t) {
		return w.H.useOptimistic(e, t);
	}, e.useReducer = function(e, t, n) {
		return w.H.useReducer(e, t, n);
	}, e.useRef = function(e) {
		return w.H.useRef(e);
	}, e.useState = function(e) {
		return w.H.useState(e);
	}, e.useSyncExternalStore = function(e, t, n) {
		return w.H.useSyncExternalStore(e, t, n);
	}, e.useTransition = function() {
		return w.H.useTransition();
	}, e.version = "19.2.7";
})), le = /* @__PURE__ */ n(((e, t) => {
	t.exports = ce();
})), ue = /* @__PURE__ */ n(((e) => {
	function t(e, t) {
		var n = e.length;
		e.push(t);
		a: for (; 0 < n;) {
			var r = n - 1 >>> 1, a = e[r];
			if (0 < i(a, t)) e[r] = t, e[n] = a, n = r;
			else break a;
		}
	}
	function n(e) {
		return e.length === 0 ? null : e[0];
	}
	function r(e) {
		if (e.length === 0) return null;
		var t = e[0], n = e.pop();
		if (n !== t) {
			e[0] = n;
			a: for (var r = 0, a = e.length, o = a >>> 1; r < o;) {
				var s = 2 * (r + 1) - 1, c = e[s], l = s + 1, u = e[l];
				if (0 > i(c, n)) l < a && 0 > i(u, c) ? (e[r] = u, e[l] = n, r = l) : (e[r] = c, e[s] = n, r = s);
				else if (l < a && 0 > i(u, n)) e[r] = u, e[l] = n, r = l;
				else break a;
			}
		}
		return t;
	}
	function i(e, t) {
		var n = e.sortIndex - t.sortIndex;
		return n === 0 ? e.id - t.id : n;
	}
	if (e.unstable_now = void 0, typeof performance == "object" && typeof performance.now == "function") {
		var a = performance;
		e.unstable_now = function() {
			return a.now();
		};
	} else {
		var o = Date, s = o.now();
		e.unstable_now = function() {
			return o.now() - s;
		};
	}
	var c = [], l = [], u = 1, d = null, f = 3, p = !1, m = !1, h = !1, g = !1, _ = typeof setTimeout == "function" ? setTimeout : null, v = typeof clearTimeout == "function" ? clearTimeout : null, y = typeof setImmediate < "u" ? setImmediate : null;
	function b(e) {
		for (var i = n(l); i !== null;) {
			if (i.callback === null) r(l);
			else if (i.startTime <= e) r(l), i.sortIndex = i.expirationTime, t(c, i);
			else break;
			i = n(l);
		}
	}
	function x(e) {
		if (h = !1, b(e), !m) if (n(c) !== null) m = !0, S || (S = !0, O());
		else {
			var t = n(l);
			t !== null && A(x, t.startTime - e);
		}
	}
	var S = !1, C = -1, w = 5, T = -1;
	function E() {
		return g ? !0 : !(e.unstable_now() - T < w);
	}
	function D() {
		if (g = !1, S) {
			var t = e.unstable_now();
			T = t;
			var i = !0;
			try {
				a: {
					m = !1, h && (h = !1, v(C), C = -1), p = !0;
					var a = f;
					try {
						b: {
							for (b(t), d = n(c); d !== null && !(d.expirationTime > t && E());) {
								var o = d.callback;
								if (typeof o == "function") {
									d.callback = null, f = d.priorityLevel;
									var s = o(d.expirationTime <= t);
									if (t = e.unstable_now(), typeof s == "function") {
										d.callback = s, b(t), i = !0;
										break b;
									}
									d === n(c) && r(c), b(t);
								} else r(c);
								d = n(c);
							}
							if (d !== null) i = !0;
							else {
								var u = n(l);
								u !== null && A(x, u.startTime - t), i = !1;
							}
						}
						break a;
					} finally {
						d = null, f = a, p = !1;
					}
					i = void 0;
				}
			} finally {
				i ? O() : S = !1;
			}
		}
	}
	var O;
	if (typeof y == "function") O = function() {
		y(D);
	};
	else if (typeof MessageChannel < "u") {
		var k = new MessageChannel(), ee = k.port2;
		k.port1.onmessage = D, O = function() {
			ee.postMessage(null);
		};
	} else O = function() {
		_(D, 0);
	};
	function A(t, n) {
		C = _(function() {
			t(e.unstable_now());
		}, n);
	}
	e.unstable_IdlePriority = 5, e.unstable_ImmediatePriority = 1, e.unstable_LowPriority = 4, e.unstable_NormalPriority = 3, e.unstable_Profiling = null, e.unstable_UserBlockingPriority = 2, e.unstable_cancelCallback = function(e) {
		e.callback = null;
	}, e.unstable_forceFrameRate = function(e) {
		0 > e || 125 < e ? console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported") : w = 0 < e ? Math.floor(1e3 / e) : 5;
	}, e.unstable_getCurrentPriorityLevel = function() {
		return f;
	}, e.unstable_next = function(e) {
		switch (f) {
			case 1:
			case 2:
			case 3:
				var t = 3;
				break;
			default: t = f;
		}
		var n = f;
		f = t;
		try {
			return e();
		} finally {
			f = n;
		}
	}, e.unstable_requestPaint = function() {
		g = !0;
	}, e.unstable_runWithPriority = function(e, t) {
		switch (e) {
			case 1:
			case 2:
			case 3:
			case 4:
			case 5: break;
			default: e = 3;
		}
		var n = f;
		f = e;
		try {
			return t();
		} finally {
			f = n;
		}
	}, e.unstable_scheduleCallback = function(r, i, a) {
		var o = e.unstable_now();
		switch (typeof a == "object" && a ? (a = a.delay, a = typeof a == "number" && 0 < a ? o + a : o) : a = o, r) {
			case 1:
				var s = -1;
				break;
			case 2:
				s = 250;
				break;
			case 5:
				s = 1073741823;
				break;
			case 4:
				s = 1e4;
				break;
			default: s = 5e3;
		}
		return s = a + s, r = {
			id: u++,
			callback: i,
			priorityLevel: r,
			startTime: a,
			expirationTime: s,
			sortIndex: -1
		}, a > o ? (r.sortIndex = a, t(l, r), n(c) === null && r === n(l) && (h ? (v(C), C = -1) : h = !0, A(x, a - o))) : (r.sortIndex = s, t(c, r), m || p || (m = !0, S || (S = !0, O()))), r;
	}, e.unstable_shouldYield = E, e.unstable_wrapCallback = function(e) {
		var t = f;
		return function() {
			var n = f;
			f = t;
			try {
				return e.apply(this, arguments);
			} finally {
				f = n;
			}
		};
	};
})), de = /* @__PURE__ */ n(((e, t) => {
	t.exports = ue();
})), fe = /* @__PURE__ */ n(((e) => {
	var t = le();
	function n(e) {
		var t = "https://react.dev/errors/" + e;
		if (1 < arguments.length) {
			t += "?args[]=" + encodeURIComponent(arguments[1]);
			for (var n = 2; n < arguments.length; n++) t += "&args[]=" + encodeURIComponent(arguments[n]);
		}
		return "Minified React error #" + e + "; visit " + t + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
	}
	function r() {}
	var i = {
		d: {
			f: r,
			r: function() {
				throw Error(n(522));
			},
			D: r,
			C: r,
			L: r,
			m: r,
			X: r,
			S: r,
			M: r
		},
		p: 0,
		findDOMNode: null
	}, a = Symbol.for("react.portal");
	function o(e, t, n) {
		var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
		return {
			$$typeof: a,
			key: r == null ? null : "" + r,
			children: e,
			containerInfo: t,
			implementation: n
		};
	}
	var s = t.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE;
	function c(e, t) {
		if (e === "font") return "";
		if (typeof t == "string") return t === "use-credentials" ? t : "";
	}
	e.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE = i, e.createPortal = function(e, t) {
		var r = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
		if (!t || t.nodeType !== 1 && t.nodeType !== 9 && t.nodeType !== 11) throw Error(n(299));
		return o(e, t, null, r);
	}, e.flushSync = function(e) {
		var t = s.T, n = i.p;
		try {
			if (s.T = null, i.p = 2, e) return e();
		} finally {
			s.T = t, i.p = n, i.d.f();
		}
	}, e.preconnect = function(e, t) {
		typeof e == "string" && (t ? (t = t.crossOrigin, t = typeof t == "string" ? t === "use-credentials" ? t : "" : void 0) : t = null, i.d.C(e, t));
	}, e.prefetchDNS = function(e) {
		typeof e == "string" && i.d.D(e);
	}, e.preinit = function(e, t) {
		if (typeof e == "string" && t && typeof t.as == "string") {
			var n = t.as, r = c(n, t.crossOrigin), a = typeof t.integrity == "string" ? t.integrity : void 0, o = typeof t.fetchPriority == "string" ? t.fetchPriority : void 0;
			n === "style" ? i.d.S(e, typeof t.precedence == "string" ? t.precedence : void 0, {
				crossOrigin: r,
				integrity: a,
				fetchPriority: o
			}) : n === "script" && i.d.X(e, {
				crossOrigin: r,
				integrity: a,
				fetchPriority: o,
				nonce: typeof t.nonce == "string" ? t.nonce : void 0
			});
		}
	}, e.preinitModule = function(e, t) {
		if (typeof e == "string") if (typeof t == "object" && t) {
			if (t.as == null || t.as === "script") {
				var n = c(t.as, t.crossOrigin);
				i.d.M(e, {
					crossOrigin: n,
					integrity: typeof t.integrity == "string" ? t.integrity : void 0,
					nonce: typeof t.nonce == "string" ? t.nonce : void 0
				});
			}
		} else t ?? i.d.M(e);
	}, e.preload = function(e, t) {
		if (typeof e == "string" && typeof t == "object" && t && typeof t.as == "string") {
			var n = t.as, r = c(n, t.crossOrigin);
			i.d.L(e, n, {
				crossOrigin: r,
				integrity: typeof t.integrity == "string" ? t.integrity : void 0,
				nonce: typeof t.nonce == "string" ? t.nonce : void 0,
				type: typeof t.type == "string" ? t.type : void 0,
				fetchPriority: typeof t.fetchPriority == "string" ? t.fetchPriority : void 0,
				referrerPolicy: typeof t.referrerPolicy == "string" ? t.referrerPolicy : void 0,
				imageSrcSet: typeof t.imageSrcSet == "string" ? t.imageSrcSet : void 0,
				imageSizes: typeof t.imageSizes == "string" ? t.imageSizes : void 0,
				media: typeof t.media == "string" ? t.media : void 0
			});
		}
	}, e.preloadModule = function(e, t) {
		if (typeof e == "string") if (t) {
			var n = c(t.as, t.crossOrigin);
			i.d.m(e, {
				as: typeof t.as == "string" && t.as !== "script" ? t.as : void 0,
				crossOrigin: n,
				integrity: typeof t.integrity == "string" ? t.integrity : void 0
			});
		} else i.d.m(e);
	}, e.requestFormReset = function(e) {
		i.d.r(e);
	}, e.unstable_batchedUpdates = function(e, t) {
		return e(t);
	}, e.useFormState = function(e, t, n) {
		return s.H.useFormState(e, t, n);
	}, e.useFormStatus = function() {
		return s.H.useHostTransitionStatus();
	}, e.version = "19.2.7";
})), pe = /* @__PURE__ */ n(((e, t) => {
	function n() {
		if (!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function")) try {
			__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(n);
		} catch (e) {
			console.error(e);
		}
	}
	n(), t.exports = fe();
})), me = /* @__PURE__ */ n(((e) => {
	var t = de(), n = le(), r = pe();
	function i(e) {
		var t = "https://react.dev/errors/" + e;
		if (1 < arguments.length) {
			t += "?args[]=" + encodeURIComponent(arguments[1]);
			for (var n = 2; n < arguments.length; n++) t += "&args[]=" + encodeURIComponent(arguments[n]);
		}
		return "Minified React error #" + e + "; visit " + t + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
	}
	function a(e) {
		return !(!e || e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11);
	}
	function o(e) {
		var t = e, n = e;
		if (e.alternate) for (; t.return;) t = t.return;
		else {
			e = t;
			do
				t = e, t.flags & 4098 && (n = t.return), e = t.return;
			while (e);
		}
		return t.tag === 3 ? n : null;
	}
	function s(e) {
		if (e.tag === 13) {
			var t = e.memoizedState;
			if (t === null && (e = e.alternate, e !== null && (t = e.memoizedState)), t !== null) return t.dehydrated;
		}
		return null;
	}
	function c(e) {
		if (e.tag === 31) {
			var t = e.memoizedState;
			if (t === null && (e = e.alternate, e !== null && (t = e.memoizedState)), t !== null) return t.dehydrated;
		}
		return null;
	}
	function l(e) {
		if (o(e) !== e) throw Error(i(188));
	}
	function u(e) {
		var t = e.alternate;
		if (!t) {
			if (t = o(e), t === null) throw Error(i(188));
			return t === e ? e : null;
		}
		for (var n = e, r = t;;) {
			var a = n.return;
			if (a === null) break;
			var s = a.alternate;
			if (s === null) {
				if (r = a.return, r !== null) {
					n = r;
					continue;
				}
				break;
			}
			if (a.child === s.child) {
				for (s = a.child; s;) {
					if (s === n) return l(a), e;
					if (s === r) return l(a), t;
					s = s.sibling;
				}
				throw Error(i(188));
			}
			if (n.return !== r.return) n = a, r = s;
			else {
				for (var c = !1, u = a.child; u;) {
					if (u === n) {
						c = !0, n = a, r = s;
						break;
					}
					if (u === r) {
						c = !0, r = a, n = s;
						break;
					}
					u = u.sibling;
				}
				if (!c) {
					for (u = s.child; u;) {
						if (u === n) {
							c = !0, n = s, r = a;
							break;
						}
						if (u === r) {
							c = !0, r = s, n = a;
							break;
						}
						u = u.sibling;
					}
					if (!c) throw Error(i(189));
				}
			}
			if (n.alternate !== r) throw Error(i(190));
		}
		if (n.tag !== 3) throw Error(i(188));
		return n.stateNode.current === n ? e : t;
	}
	function d(e) {
		var t = e.tag;
		if (t === 5 || t === 26 || t === 27 || t === 6) return e;
		for (e = e.child; e !== null;) {
			if (t = d(e), t !== null) return t;
			e = e.sibling;
		}
		return null;
	}
	var f = Object.assign, p = Symbol.for("react.element"), m = Symbol.for("react.transitional.element"), h = Symbol.for("react.portal"), g = Symbol.for("react.fragment"), _ = Symbol.for("react.strict_mode"), v = Symbol.for("react.profiler"), y = Symbol.for("react.consumer"), b = Symbol.for("react.context"), x = Symbol.for("react.forward_ref"), S = Symbol.for("react.suspense"), C = Symbol.for("react.suspense_list"), w = Symbol.for("react.memo"), T = Symbol.for("react.lazy"), E = Symbol.for("react.activity"), D = Symbol.for("react.memo_cache_sentinel"), O = Symbol.iterator;
	function k(e) {
		return typeof e != "object" || !e ? null : (e = O && e[O] || e["@@iterator"], typeof e == "function" ? e : null);
	}
	var ee = Symbol.for("react.client.reference");
	function A(e) {
		if (e == null) return null;
		if (typeof e == "function") return e.$$typeof === ee ? null : e.displayName || e.name || null;
		if (typeof e == "string") return e;
		switch (e) {
			case g: return "Fragment";
			case v: return "Profiler";
			case _: return "StrictMode";
			case S: return "Suspense";
			case C: return "SuspenseList";
			case E: return "Activity";
		}
		if (typeof e == "object") switch (e.$$typeof) {
			case h: return "Portal";
			case b: return e.displayName || "Context";
			case y: return (e._context.displayName || "Context") + ".Consumer";
			case x:
				var t = e.render;
				return e = e.displayName, e ||= (e = t.displayName || t.name || "", e === "" ? "ForwardRef" : "ForwardRef(" + e + ")"), e;
			case w: return t = e.displayName || null, t === null ? A(e.type) || "Memo" : t;
			case T:
				t = e._payload, e = e._init;
				try {
					return A(e(t));
				} catch {}
		}
		return null;
	}
	var j = Array.isArray, M = n.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE, N = r.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE, P = {
		pending: !1,
		data: null,
		method: null,
		action: null
	}, te = [], ne = -1;
	function re(e) {
		return { current: e };
	}
	function ie(e) {
		0 > ne || (e.current = te[ne], te[ne] = null, ne--);
	}
	function F(e, t) {
		ne++, te[ne] = e.current, e.current = t;
	}
	var ae = re(null), oe = re(null), se = re(null), ce = re(null);
	function ue(e, t) {
		switch (F(se, t), F(oe, e), F(ae, null), t.nodeType) {
			case 9:
			case 11:
				e = (e = t.documentElement) && (e = e.namespaceURI) ? Gd(e) : 0;
				break;
			default: if (e = t.tagName, t = t.namespaceURI) t = Gd(t), e = Kd(t, e);
			else switch (e) {
				case "svg":
					e = 1;
					break;
				case "math":
					e = 2;
					break;
				default: e = 0;
			}
		}
		ie(ae), F(ae, e);
	}
	function fe() {
		ie(ae), ie(oe), ie(se);
	}
	function me(e) {
		e.memoizedState !== null && F(ce, e);
		var t = ae.current, n = Kd(t, e.type);
		t !== n && (F(oe, e), F(ae, n));
	}
	function he(e) {
		oe.current === e && (ie(ae), ie(oe)), ce.current === e && (ie(ce), np._currentValue = P);
	}
	var I, ge;
	function _e(e) {
		if (I === void 0) try {
			throw Error();
		} catch (e) {
			var t = e.stack.trim().match(/\n( *(at )?)/);
			I = t && t[1] || "", ge = -1 < e.stack.indexOf("\n    at") ? " (<anonymous>)" : -1 < e.stack.indexOf("@") ? "@unknown:0:0" : "";
		}
		return "\n" + I + e + ge;
	}
	var ve = !1;
	function ye(e, t) {
		if (!e || ve) return "";
		ve = !0;
		var n = Error.prepareStackTrace;
		Error.prepareStackTrace = void 0;
		try {
			var r = { DetermineComponentFrameRoot: function() {
				try {
					if (t) {
						var n = function() {
							throw Error();
						};
						if (Object.defineProperty(n.prototype, "props", { set: function() {
							throw Error();
						} }), typeof Reflect == "object" && Reflect.construct) {
							try {
								Reflect.construct(n, []);
							} catch (e) {
								var r = e;
							}
							Reflect.construct(e, [], n);
						} else {
							try {
								n.call();
							} catch (e) {
								r = e;
							}
							e.call(n.prototype);
						}
					} else {
						try {
							throw Error();
						} catch (e) {
							r = e;
						}
						(n = e()) && typeof n.catch == "function" && n.catch(function() {});
					}
				} catch (e) {
					if (e && r && typeof e.stack == "string") return [e.stack, r.stack];
				}
				return [null, null];
			} };
			r.DetermineComponentFrameRoot.displayName = "DetermineComponentFrameRoot";
			var i = Object.getOwnPropertyDescriptor(r.DetermineComponentFrameRoot, "name");
			i && i.configurable && Object.defineProperty(r.DetermineComponentFrameRoot, "name", { value: "DetermineComponentFrameRoot" });
			var a = r.DetermineComponentFrameRoot(), o = a[0], s = a[1];
			if (o && s) {
				var c = o.split("\n"), l = s.split("\n");
				for (i = r = 0; r < c.length && !c[r].includes("DetermineComponentFrameRoot");) r++;
				for (; i < l.length && !l[i].includes("DetermineComponentFrameRoot");) i++;
				if (r === c.length || i === l.length) for (r = c.length - 1, i = l.length - 1; 1 <= r && 0 <= i && c[r] !== l[i];) i--;
				for (; 1 <= r && 0 <= i; r--, i--) if (c[r] !== l[i]) {
					if (r !== 1 || i !== 1) do
						if (r--, i--, 0 > i || c[r] !== l[i]) {
							var u = "\n" + c[r].replace(" at new ", " at ");
							return e.displayName && u.includes("<anonymous>") && (u = u.replace("<anonymous>", e.displayName)), u;
						}
					while (1 <= r && 0 <= i);
					break;
				}
			}
		} finally {
			ve = !1, Error.prepareStackTrace = n;
		}
		return (n = e ? e.displayName || e.name : "") ? _e(n) : "";
	}
	function be(e, t) {
		switch (e.tag) {
			case 26:
			case 27:
			case 5: return _e(e.type);
			case 16: return _e("Lazy");
			case 13: return e.child !== t && t !== null ? _e("Suspense Fallback") : _e("Suspense");
			case 19: return _e("SuspenseList");
			case 0:
			case 15: return ye(e.type, !1);
			case 11: return ye(e.type.render, !1);
			case 1: return ye(e.type, !0);
			case 31: return _e("Activity");
			default: return "";
		}
	}
	function xe(e) {
		try {
			var t = "", n = null;
			do
				t += be(e, n), n = e, e = e.return;
			while (e);
			return t;
		} catch (e) {
			return "\nError generating stack: " + e.message + "\n" + e.stack;
		}
	}
	var L = Object.prototype.hasOwnProperty, Se = t.unstable_scheduleCallback, Ce = t.unstable_cancelCallback, we = t.unstable_shouldYield, Te = t.unstable_requestPaint, Ee = t.unstable_now, De = t.unstable_getCurrentPriorityLevel, Oe = t.unstable_ImmediatePriority, ke = t.unstable_UserBlockingPriority, Ae = t.unstable_NormalPriority, je = t.unstable_LowPriority, Me = t.unstable_IdlePriority, Ne = t.log, Pe = t.unstable_setDisableYieldValue, Fe = null, Ie = null;
	function Le(e) {
		if (typeof Ne == "function" && Pe(e), Ie && typeof Ie.setStrictMode == "function") try {
			Ie.setStrictMode(Fe, e);
		} catch {}
	}
	var Re = Math.clz32 ? Math.clz32 : Ve, ze = Math.log, Be = Math.LN2;
	function Ve(e) {
		return e >>>= 0, e === 0 ? 32 : 31 - (ze(e) / Be | 0) | 0;
	}
	var He = 256, Ue = 262144, We = 4194304;
	function Ge(e) {
		var t = e & 42;
		if (t !== 0) return t;
		switch (e & -e) {
			case 1: return 1;
			case 2: return 2;
			case 4: return 4;
			case 8: return 8;
			case 16: return 16;
			case 32: return 32;
			case 64: return 64;
			case 128: return 128;
			case 256:
			case 512:
			case 1024:
			case 2048:
			case 4096:
			case 8192:
			case 16384:
			case 32768:
			case 65536:
			case 131072: return e & 261888;
			case 262144:
			case 524288:
			case 1048576:
			case 2097152: return e & 3932160;
			case 4194304:
			case 8388608:
			case 16777216:
			case 33554432: return e & 62914560;
			case 67108864: return 67108864;
			case 134217728: return 134217728;
			case 268435456: return 268435456;
			case 536870912: return 536870912;
			case 1073741824: return 0;
			default: return e;
		}
	}
	function Ke(e, t, n) {
		var r = e.pendingLanes;
		if (r === 0) return 0;
		var i = 0, a = e.suspendedLanes, o = e.pingedLanes;
		e = e.warmLanes;
		var s = r & 134217727;
		return s === 0 ? (s = r & ~a, s === 0 ? o === 0 ? n || (n = r & ~e, n !== 0 && (i = Ge(n))) : i = Ge(o) : i = Ge(s)) : (r = s & ~a, r === 0 ? (o &= s, o === 0 ? n || (n = s & ~e, n !== 0 && (i = Ge(n))) : i = Ge(o)) : i = Ge(r)), i === 0 ? 0 : t !== 0 && t !== i && (t & a) === 0 && (a = i & -i, n = t & -t, a >= n || a === 32 && n & 4194048) ? t : i;
	}
	function qe(e, t) {
		return (e.pendingLanes & ~(e.suspendedLanes & ~e.pingedLanes) & t) === 0;
	}
	function Je(e, t) {
		switch (e) {
			case 1:
			case 2:
			case 4:
			case 8:
			case 64: return t + 250;
			case 16:
			case 32:
			case 128:
			case 256:
			case 512:
			case 1024:
			case 2048:
			case 4096:
			case 8192:
			case 16384:
			case 32768:
			case 65536:
			case 131072:
			case 262144:
			case 524288:
			case 1048576:
			case 2097152: return t + 5e3;
			case 4194304:
			case 8388608:
			case 16777216:
			case 33554432: return -1;
			case 67108864:
			case 134217728:
			case 268435456:
			case 536870912:
			case 1073741824: return -1;
			default: return -1;
		}
	}
	function Ye() {
		var e = We;
		return We <<= 1, !(We & 62914560) && (We = 4194304), e;
	}
	function Xe(e) {
		for (var t = [], n = 0; 31 > n; n++) t.push(e);
		return t;
	}
	function Ze(e, t) {
		e.pendingLanes |= t, t !== 268435456 && (e.suspendedLanes = 0, e.pingedLanes = 0, e.warmLanes = 0);
	}
	function Qe(e, t, n, r, i, a) {
		var o = e.pendingLanes;
		e.pendingLanes = n, e.suspendedLanes = 0, e.pingedLanes = 0, e.warmLanes = 0, e.expiredLanes &= n, e.entangledLanes &= n, e.errorRecoveryDisabledLanes &= n, e.shellSuspendCounter = 0;
		var s = e.entanglements, c = e.expirationTimes, l = e.hiddenUpdates;
		for (n = o & ~n; 0 < n;) {
			var u = 31 - Re(n), d = 1 << u;
			s[u] = 0, c[u] = -1;
			var f = l[u];
			if (f !== null) for (l[u] = null, u = 0; u < f.length; u++) {
				var p = f[u];
				p !== null && (p.lane &= -536870913);
			}
			n &= ~d;
		}
		r !== 0 && $e(e, r, 0), a !== 0 && i === 0 && e.tag !== 0 && (e.suspendedLanes |= a & ~(o & ~t));
	}
	function $e(e, t, n) {
		e.pendingLanes |= t, e.suspendedLanes &= ~t;
		var r = 31 - Re(t);
		e.entangledLanes |= t, e.entanglements[r] = e.entanglements[r] | 1073741824 | n & 261930;
	}
	function et(e, t) {
		var n = e.entangledLanes |= t;
		for (e = e.entanglements; n;) {
			var r = 31 - Re(n), i = 1 << r;
			i & t | e[r] & t && (e[r] |= t), n &= ~i;
		}
	}
	function tt(e, t) {
		var n = t & -t;
		return n = n & 42 ? 1 : nt(n), (n & (e.suspendedLanes | t)) === 0 ? n : 0;
	}
	function nt(e) {
		switch (e) {
			case 2:
				e = 1;
				break;
			case 8:
				e = 4;
				break;
			case 32:
				e = 16;
				break;
			case 256:
			case 512:
			case 1024:
			case 2048:
			case 4096:
			case 8192:
			case 16384:
			case 32768:
			case 65536:
			case 131072:
			case 262144:
			case 524288:
			case 1048576:
			case 2097152:
			case 4194304:
			case 8388608:
			case 16777216:
			case 33554432:
				e = 128;
				break;
			case 268435456:
				e = 134217728;
				break;
			default: e = 0;
		}
		return e;
	}
	function rt(e) {
		return e &= -e, 2 < e ? 8 < e ? e & 134217727 ? 32 : 268435456 : 8 : 2;
	}
	function R() {
		var e = N.p;
		return e === 0 ? (e = window.event, e === void 0 ? 32 : vp(e.type)) : e;
	}
	function it(e, t) {
		var n = N.p;
		try {
			return N.p = e, t();
		} finally {
			N.p = n;
		}
	}
	var at = Math.random().toString(36).slice(2), ot = "__reactFiber$" + at, st = "__reactProps$" + at, ct = "__reactContainer$" + at, lt = "__reactEvents$" + at, ut = "__reactListeners$" + at, dt = "__reactHandles$" + at, ft = "__reactResources$" + at, pt = "__reactMarker$" + at;
	function mt(e) {
		delete e[ot], delete e[st], delete e[lt], delete e[ut], delete e[dt];
	}
	function ht(e) {
		var t = e[ot];
		if (t) return t;
		for (var n = e.parentNode; n;) {
			if (t = n[ct] || n[ot]) {
				if (n = t.alternate, t.child !== null || n !== null && n.child !== null) for (e = hf(e); e !== null;) {
					if (n = e[ot]) return n;
					e = hf(e);
				}
				return t;
			}
			e = n, n = e.parentNode;
		}
		return null;
	}
	function gt(e) {
		if (e = e[ot] || e[ct]) {
			var t = e.tag;
			if (t === 5 || t === 6 || t === 13 || t === 31 || t === 26 || t === 27 || t === 3) return e;
		}
		return null;
	}
	function _t(e) {
		var t = e.tag;
		if (t === 5 || t === 26 || t === 27 || t === 6) return e.stateNode;
		throw Error(i(33));
	}
	function vt(e) {
		var t = e[ft];
		return t ||= e[ft] = {
			hoistableStyles: /* @__PURE__ */ new Map(),
			hoistableScripts: /* @__PURE__ */ new Map()
		}, t;
	}
	function yt(e) {
		e[pt] = !0;
	}
	var bt = /* @__PURE__ */ new Set(), xt = {};
	function St(e, t) {
		Ct(e, t), Ct(e + "Capture", t);
	}
	function Ct(e, t) {
		for (xt[e] = t, e = 0; e < t.length; e++) bt.add(t[e]);
	}
	var wt = RegExp("^[:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD][:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD\\-.0-9\\u00B7\\u0300-\\u036F\\u203F-\\u2040]*$"), Tt = {}, Et = {};
	function Dt(e) {
		return L.call(Et, e) ? !0 : L.call(Tt, e) ? !1 : wt.test(e) ? Et[e] = !0 : (Tt[e] = !0, !1);
	}
	function Ot(e, t, n) {
		if (Dt(t)) if (n === null) e.removeAttribute(t);
		else {
			switch (typeof n) {
				case "undefined":
				case "function":
				case "symbol":
					e.removeAttribute(t);
					return;
				case "boolean":
					var r = t.toLowerCase().slice(0, 5);
					if (r !== "data-" && r !== "aria-") {
						e.removeAttribute(t);
						return;
					}
			}
			e.setAttribute(t, "" + n);
		}
	}
	function kt(e, t, n) {
		if (n === null) e.removeAttribute(t);
		else {
			switch (typeof n) {
				case "undefined":
				case "function":
				case "symbol":
				case "boolean":
					e.removeAttribute(t);
					return;
			}
			e.setAttribute(t, "" + n);
		}
	}
	function At(e, t, n, r) {
		if (r === null) e.removeAttribute(n);
		else {
			switch (typeof r) {
				case "undefined":
				case "function":
				case "symbol":
				case "boolean":
					e.removeAttribute(n);
					return;
			}
			e.setAttributeNS(t, n, "" + r);
		}
	}
	function jt(e) {
		switch (typeof e) {
			case "bigint":
			case "boolean":
			case "number":
			case "string":
			case "undefined": return e;
			case "object": return e;
			default: return "";
		}
	}
	function Mt(e) {
		var t = e.type;
		return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio");
	}
	function Nt(e, t, n) {
		var r = Object.getOwnPropertyDescriptor(e.constructor.prototype, t);
		if (!e.hasOwnProperty(t) && r !== void 0 && typeof r.get == "function" && typeof r.set == "function") {
			var i = r.get, a = r.set;
			return Object.defineProperty(e, t, {
				configurable: !0,
				get: function() {
					return i.call(this);
				},
				set: function(e) {
					n = "" + e, a.call(this, e);
				}
			}), Object.defineProperty(e, t, { enumerable: r.enumerable }), {
				getValue: function() {
					return n;
				},
				setValue: function(e) {
					n = "" + e;
				},
				stopTracking: function() {
					e._valueTracker = null, delete e[t];
				}
			};
		}
	}
	function Pt(e) {
		if (!e._valueTracker) {
			var t = Mt(e) ? "checked" : "value";
			e._valueTracker = Nt(e, t, "" + e[t]);
		}
	}
	function Ft(e) {
		if (!e) return !1;
		var t = e._valueTracker;
		if (!t) return !0;
		var n = t.getValue(), r = "";
		return e && (r = Mt(e) ? e.checked ? "true" : "false" : e.value), e = r, e === n ? !1 : (t.setValue(e), !0);
	}
	function It(e) {
		if (e ||= typeof document < "u" ? document : void 0, e === void 0) return null;
		try {
			return e.activeElement || e.body;
		} catch {
			return e.body;
		}
	}
	var Lt = /[\n"\\]/g;
	function Rt(e) {
		return e.replace(Lt, function(e) {
			return "\\" + e.charCodeAt(0).toString(16) + " ";
		});
	}
	function zt(e, t, n, r, i, a, o, s) {
		e.name = "", o != null && typeof o != "function" && typeof o != "symbol" && typeof o != "boolean" ? e.type = o : e.removeAttribute("type"), t == null ? o !== "submit" && o !== "reset" || e.removeAttribute("value") : o === "number" ? (t === 0 && e.value === "" || e.value != t) && (e.value = "" + jt(t)) : e.value !== "" + jt(t) && (e.value = "" + jt(t)), t == null ? n == null ? r != null && e.removeAttribute("value") : Vt(e, o, jt(n)) : Vt(e, o, jt(t)), i == null && a != null && (e.defaultChecked = !!a), i != null && (e.checked = i && typeof i != "function" && typeof i != "symbol"), s != null && typeof s != "function" && typeof s != "symbol" && typeof s != "boolean" ? e.name = "" + jt(s) : e.removeAttribute("name");
	}
	function Bt(e, t, n, r, i, a, o, s) {
		if (a != null && typeof a != "function" && typeof a != "symbol" && typeof a != "boolean" && (e.type = a), t != null || n != null) {
			if (!(a !== "submit" && a !== "reset" || t != null)) {
				Pt(e);
				return;
			}
			n = n == null ? "" : "" + jt(n), t = t == null ? n : "" + jt(t), s || t === e.value || (e.value = t), e.defaultValue = t;
		}
		r ??= i, r = typeof r != "function" && typeof r != "symbol" && !!r, e.checked = s ? e.checked : !!r, e.defaultChecked = !!r, o != null && typeof o != "function" && typeof o != "symbol" && typeof o != "boolean" && (e.name = o), Pt(e);
	}
	function Vt(e, t, n) {
		t === "number" && It(e.ownerDocument) === e || e.defaultValue === "" + n || (e.defaultValue = "" + n);
	}
	function Ht(e, t, n, r) {
		if (e = e.options, t) {
			t = {};
			for (var i = 0; i < n.length; i++) t["$" + n[i]] = !0;
			for (n = 0; n < e.length; n++) i = t.hasOwnProperty("$" + e[n].value), e[n].selected !== i && (e[n].selected = i), i && r && (e[n].defaultSelected = !0);
		} else {
			for (n = "" + jt(n), t = null, i = 0; i < e.length; i++) {
				if (e[i].value === n) {
					e[i].selected = !0, r && (e[i].defaultSelected = !0);
					return;
				}
				t !== null || e[i].disabled || (t = e[i]);
			}
			t !== null && (t.selected = !0);
		}
	}
	function Ut(e, t, n) {
		if (t != null && (t = "" + jt(t), t !== e.value && (e.value = t), n == null)) {
			e.defaultValue !== t && (e.defaultValue = t);
			return;
		}
		e.defaultValue = n == null ? "" : "" + jt(n);
	}
	function Wt(e, t, n, r) {
		if (t == null) {
			if (r != null) {
				if (n != null) throw Error(i(92));
				if (j(r)) {
					if (1 < r.length) throw Error(i(93));
					r = r[0];
				}
				n = r;
			}
			n ??= "", t = n;
		}
		n = jt(t), e.defaultValue = n, r = e.textContent, r === n && r !== "" && r !== null && (e.value = r), Pt(e);
	}
	function Gt(e, t) {
		if (t) {
			var n = e.firstChild;
			if (n && n === e.lastChild && n.nodeType === 3) {
				n.nodeValue = t;
				return;
			}
		}
		e.textContent = t;
	}
	var Kt = new Set("animationIterationCount aspectRatio borderImageOutset borderImageSlice borderImageWidth boxFlex boxFlexGroup boxOrdinalGroup columnCount columns flex flexGrow flexPositive flexShrink flexNegative flexOrder gridArea gridRow gridRowEnd gridRowSpan gridRowStart gridColumn gridColumnEnd gridColumnSpan gridColumnStart fontWeight lineClamp lineHeight opacity order orphans scale tabSize widows zIndex zoom fillOpacity floodOpacity stopOpacity strokeDasharray strokeDashoffset strokeMiterlimit strokeOpacity strokeWidth MozAnimationIterationCount MozBoxFlex MozBoxFlexGroup MozLineClamp msAnimationIterationCount msFlex msZoom msFlexGrow msFlexNegative msFlexOrder msFlexPositive msFlexShrink msGridColumn msGridColumnSpan msGridRow msGridRowSpan WebkitAnimationIterationCount WebkitBoxFlex WebKitBoxFlexGroup WebkitBoxOrdinalGroup WebkitColumnCount WebkitColumns WebkitFlex WebkitFlexGrow WebkitFlexPositive WebkitFlexShrink WebkitLineClamp".split(" "));
	function qt(e, t, n) {
		var r = t.indexOf("--") === 0;
		n == null || typeof n == "boolean" || n === "" ? r ? e.setProperty(t, "") : t === "float" ? e.cssFloat = "" : e[t] = "" : r ? e.setProperty(t, n) : typeof n != "number" || n === 0 || Kt.has(t) ? t === "float" ? e.cssFloat = n : e[t] = ("" + n).trim() : e[t] = n + "px";
	}
	function Jt(e, t, n) {
		if (t != null && typeof t != "object") throw Error(i(62));
		if (e = e.style, n != null) {
			for (var r in n) !n.hasOwnProperty(r) || t != null && t.hasOwnProperty(r) || (r.indexOf("--") === 0 ? e.setProperty(r, "") : r === "float" ? e.cssFloat = "" : e[r] = "");
			for (var a in t) r = t[a], t.hasOwnProperty(a) && n[a] !== r && qt(e, a, r);
		} else for (var o in t) t.hasOwnProperty(o) && qt(e, o, t[o]);
	}
	function Yt(e) {
		if (e.indexOf("-") === -1) return !1;
		switch (e) {
			case "annotation-xml":
			case "color-profile":
			case "font-face":
			case "font-face-src":
			case "font-face-uri":
			case "font-face-format":
			case "font-face-name":
			case "missing-glyph": return !1;
			default: return !0;
		}
	}
	var Xt = /* @__PURE__ */ new Map([
		["acceptCharset", "accept-charset"],
		["htmlFor", "for"],
		["httpEquiv", "http-equiv"],
		["crossOrigin", "crossorigin"],
		["accentHeight", "accent-height"],
		["alignmentBaseline", "alignment-baseline"],
		["arabicForm", "arabic-form"],
		["baselineShift", "baseline-shift"],
		["capHeight", "cap-height"],
		["clipPath", "clip-path"],
		["clipRule", "clip-rule"],
		["colorInterpolation", "color-interpolation"],
		["colorInterpolationFilters", "color-interpolation-filters"],
		["colorProfile", "color-profile"],
		["colorRendering", "color-rendering"],
		["dominantBaseline", "dominant-baseline"],
		["enableBackground", "enable-background"],
		["fillOpacity", "fill-opacity"],
		["fillRule", "fill-rule"],
		["floodColor", "flood-color"],
		["floodOpacity", "flood-opacity"],
		["fontFamily", "font-family"],
		["fontSize", "font-size"],
		["fontSizeAdjust", "font-size-adjust"],
		["fontStretch", "font-stretch"],
		["fontStyle", "font-style"],
		["fontVariant", "font-variant"],
		["fontWeight", "font-weight"],
		["glyphName", "glyph-name"],
		["glyphOrientationHorizontal", "glyph-orientation-horizontal"],
		["glyphOrientationVertical", "glyph-orientation-vertical"],
		["horizAdvX", "horiz-adv-x"],
		["horizOriginX", "horiz-origin-x"],
		["imageRendering", "image-rendering"],
		["letterSpacing", "letter-spacing"],
		["lightingColor", "lighting-color"],
		["markerEnd", "marker-end"],
		["markerMid", "marker-mid"],
		["markerStart", "marker-start"],
		["overlinePosition", "overline-position"],
		["overlineThickness", "overline-thickness"],
		["paintOrder", "paint-order"],
		["panose-1", "panose-1"],
		["pointerEvents", "pointer-events"],
		["renderingIntent", "rendering-intent"],
		["shapeRendering", "shape-rendering"],
		["stopColor", "stop-color"],
		["stopOpacity", "stop-opacity"],
		["strikethroughPosition", "strikethrough-position"],
		["strikethroughThickness", "strikethrough-thickness"],
		["strokeDasharray", "stroke-dasharray"],
		["strokeDashoffset", "stroke-dashoffset"],
		["strokeLinecap", "stroke-linecap"],
		["strokeLinejoin", "stroke-linejoin"],
		["strokeMiterlimit", "stroke-miterlimit"],
		["strokeOpacity", "stroke-opacity"],
		["strokeWidth", "stroke-width"],
		["textAnchor", "text-anchor"],
		["textDecoration", "text-decoration"],
		["textRendering", "text-rendering"],
		["transformOrigin", "transform-origin"],
		["underlinePosition", "underline-position"],
		["underlineThickness", "underline-thickness"],
		["unicodeBidi", "unicode-bidi"],
		["unicodeRange", "unicode-range"],
		["unitsPerEm", "units-per-em"],
		["vAlphabetic", "v-alphabetic"],
		["vHanging", "v-hanging"],
		["vIdeographic", "v-ideographic"],
		["vMathematical", "v-mathematical"],
		["vectorEffect", "vector-effect"],
		["vertAdvY", "vert-adv-y"],
		["vertOriginX", "vert-origin-x"],
		["vertOriginY", "vert-origin-y"],
		["wordSpacing", "word-spacing"],
		["writingMode", "writing-mode"],
		["xmlnsXlink", "xmlns:xlink"],
		["xHeight", "x-height"]
	]), Zt = /^[\u0000-\u001F ]*j[\r\n\t]*a[\r\n\t]*v[\r\n\t]*a[\r\n\t]*s[\r\n\t]*c[\r\n\t]*r[\r\n\t]*i[\r\n\t]*p[\r\n\t]*t[\r\n\t]*:/i;
	function Qt(e) {
		return Zt.test("" + e) ? "javascript:throw new Error('React has blocked a javascript: URL as a security precaution.')" : e;
	}
	function $t() {}
	var en = null;
	function tn(e) {
		return e = e.target || e.srcElement || window, e.correspondingUseElement && (e = e.correspondingUseElement), e.nodeType === 3 ? e.parentNode : e;
	}
	var nn = null, rn = null;
	function an(e) {
		var t = gt(e);
		if (t && (e = t.stateNode)) {
			var n = e[st] || null;
			a: switch (e = t.stateNode, t.type) {
				case "input":
					if (zt(e, n.value, n.defaultValue, n.defaultValue, n.checked, n.defaultChecked, n.type, n.name), t = n.name, n.type === "radio" && t != null) {
						for (n = e; n.parentNode;) n = n.parentNode;
						for (n = n.querySelectorAll("input[name=\"" + Rt("" + t) + "\"][type=\"radio\"]"), t = 0; t < n.length; t++) {
							var r = n[t];
							if (r !== e && r.form === e.form) {
								var a = r[st] || null;
								if (!a) throw Error(i(90));
								zt(r, a.value, a.defaultValue, a.defaultValue, a.checked, a.defaultChecked, a.type, a.name);
							}
						}
						for (t = 0; t < n.length; t++) r = n[t], r.form === e.form && Ft(r);
					}
					break a;
				case "textarea":
					Ut(e, n.value, n.defaultValue);
					break a;
				case "select": t = n.value, t != null && Ht(e, !!n.multiple, t, !1);
			}
		}
	}
	var on = !1;
	function sn(e, t, n) {
		if (on) return e(t, n);
		on = !0;
		try {
			return e(t);
		} finally {
			if (on = !1, (nn !== null || rn !== null) && (Cu(), nn && (t = nn, e = rn, rn = nn = null, an(t), e))) for (t = 0; t < e.length; t++) an(e[t]);
		}
	}
	function cn(e, t) {
		var n = e.stateNode;
		if (n === null) return null;
		var r = n[st] || null;
		if (r === null) return null;
		n = r[t];
		a: switch (t) {
			case "onClick":
			case "onClickCapture":
			case "onDoubleClick":
			case "onDoubleClickCapture":
			case "onMouseDown":
			case "onMouseDownCapture":
			case "onMouseMove":
			case "onMouseMoveCapture":
			case "onMouseUp":
			case "onMouseUpCapture":
			case "onMouseEnter":
				(r = !r.disabled) || (e = e.type, r = !(e === "button" || e === "input" || e === "select" || e === "textarea")), e = !r;
				break a;
			default: e = !1;
		}
		if (e) return null;
		if (n && typeof n != "function") throw Error(i(231, t, typeof n));
		return n;
	}
	var ln = !(typeof window > "u" || window.document === void 0 || window.document.createElement === void 0), un = !1;
	if (ln) try {
		var dn = {};
		Object.defineProperty(dn, "passive", { get: function() {
			un = !0;
		} }), window.addEventListener("test", dn, dn), window.removeEventListener("test", dn, dn);
	} catch {
		un = !1;
	}
	var fn = null, pn = null, mn = null;
	function hn() {
		if (mn) return mn;
		var e, t = pn, n = t.length, r, i = "value" in fn ? fn.value : fn.textContent, a = i.length;
		for (e = 0; e < n && t[e] === i[e]; e++);
		var o = n - e;
		for (r = 1; r <= o && t[n - r] === i[a - r]; r++);
		return mn = i.slice(e, 1 < r ? 1 - r : void 0);
	}
	function gn(e) {
		var t = e.keyCode;
		return "charCode" in e ? (e = e.charCode, e === 0 && t === 13 && (e = 13)) : e = t, e === 10 && (e = 13), 32 <= e || e === 13 ? e : 0;
	}
	function _n() {
		return !0;
	}
	function vn() {
		return !1;
	}
	function yn(e) {
		function t(t, n, r, i, a) {
			for (var o in this._reactName = t, this._targetInst = r, this.type = n, this.nativeEvent = i, this.target = a, this.currentTarget = null, e) e.hasOwnProperty(o) && (t = e[o], this[o] = t ? t(i) : i[o]);
			return this.isDefaultPrevented = (i.defaultPrevented == null ? !1 === i.returnValue : i.defaultPrevented) ? _n : vn, this.isPropagationStopped = vn, this;
		}
		return f(t.prototype, {
			preventDefault: function() {
				this.defaultPrevented = !0;
				var e = this.nativeEvent;
				e && (e.preventDefault ? e.preventDefault() : typeof e.returnValue != "unknown" && (e.returnValue = !1), this.isDefaultPrevented = _n);
			},
			stopPropagation: function() {
				var e = this.nativeEvent;
				e && (e.stopPropagation ? e.stopPropagation() : typeof e.cancelBubble != "unknown" && (e.cancelBubble = !0), this.isPropagationStopped = _n);
			},
			persist: function() {},
			isPersistent: _n
		}), t;
	}
	var bn = {
		eventPhase: 0,
		bubbles: 0,
		cancelable: 0,
		timeStamp: function(e) {
			return e.timeStamp || Date.now();
		},
		defaultPrevented: 0,
		isTrusted: 0
	}, xn = yn(bn), Sn = f({}, bn, {
		view: 0,
		detail: 0
	}), Cn = yn(Sn), wn, Tn, En, Dn = f({}, Sn, {
		screenX: 0,
		screenY: 0,
		clientX: 0,
		clientY: 0,
		pageX: 0,
		pageY: 0,
		ctrlKey: 0,
		shiftKey: 0,
		altKey: 0,
		metaKey: 0,
		getModifierState: Rn,
		button: 0,
		buttons: 0,
		relatedTarget: function(e) {
			return e.relatedTarget === void 0 ? e.fromElement === e.srcElement ? e.toElement : e.fromElement : e.relatedTarget;
		},
		movementX: function(e) {
			return "movementX" in e ? e.movementX : (e !== En && (En && e.type === "mousemove" ? (wn = e.screenX - En.screenX, Tn = e.screenY - En.screenY) : Tn = wn = 0, En = e), wn);
		},
		movementY: function(e) {
			return "movementY" in e ? e.movementY : Tn;
		}
	}), On = yn(Dn), kn = yn(f({}, Dn, { dataTransfer: 0 })), An = yn(f({}, Sn, { relatedTarget: 0 })), jn = yn(f({}, bn, {
		animationName: 0,
		elapsedTime: 0,
		pseudoElement: 0
	})), Mn = yn(f({}, bn, { clipboardData: function(e) {
		return "clipboardData" in e ? e.clipboardData : window.clipboardData;
	} })), Nn = yn(f({}, bn, { data: 0 })), Pn = {
		Esc: "Escape",
		Spacebar: " ",
		Left: "ArrowLeft",
		Up: "ArrowUp",
		Right: "ArrowRight",
		Down: "ArrowDown",
		Del: "Delete",
		Win: "OS",
		Menu: "ContextMenu",
		Apps: "ContextMenu",
		Scroll: "ScrollLock",
		MozPrintableKey: "Unidentified"
	}, Fn = {
		8: "Backspace",
		9: "Tab",
		12: "Clear",
		13: "Enter",
		16: "Shift",
		17: "Control",
		18: "Alt",
		19: "Pause",
		20: "CapsLock",
		27: "Escape",
		32: " ",
		33: "PageUp",
		34: "PageDown",
		35: "End",
		36: "Home",
		37: "ArrowLeft",
		38: "ArrowUp",
		39: "ArrowRight",
		40: "ArrowDown",
		45: "Insert",
		46: "Delete",
		112: "F1",
		113: "F2",
		114: "F3",
		115: "F4",
		116: "F5",
		117: "F6",
		118: "F7",
		119: "F8",
		120: "F9",
		121: "F10",
		122: "F11",
		123: "F12",
		144: "NumLock",
		145: "ScrollLock",
		224: "Meta"
	}, In = {
		Alt: "altKey",
		Control: "ctrlKey",
		Meta: "metaKey",
		Shift: "shiftKey"
	};
	function Ln(e) {
		var t = this.nativeEvent;
		return t.getModifierState ? t.getModifierState(e) : (e = In[e]) ? !!t[e] : !1;
	}
	function Rn() {
		return Ln;
	}
	var zn = yn(f({}, Sn, {
		key: function(e) {
			if (e.key) {
				var t = Pn[e.key] || e.key;
				if (t !== "Unidentified") return t;
			}
			return e.type === "keypress" ? (e = gn(e), e === 13 ? "Enter" : String.fromCharCode(e)) : e.type === "keydown" || e.type === "keyup" ? Fn[e.keyCode] || "Unidentified" : "";
		},
		code: 0,
		location: 0,
		ctrlKey: 0,
		shiftKey: 0,
		altKey: 0,
		metaKey: 0,
		repeat: 0,
		locale: 0,
		getModifierState: Rn,
		charCode: function(e) {
			return e.type === "keypress" ? gn(e) : 0;
		},
		keyCode: function(e) {
			return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
		},
		which: function(e) {
			return e.type === "keypress" ? gn(e) : e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
		}
	})), Bn = yn(f({}, Dn, {
		pointerId: 0,
		width: 0,
		height: 0,
		pressure: 0,
		tangentialPressure: 0,
		tiltX: 0,
		tiltY: 0,
		twist: 0,
		pointerType: 0,
		isPrimary: 0
	})), Vn = yn(f({}, Sn, {
		touches: 0,
		targetTouches: 0,
		changedTouches: 0,
		altKey: 0,
		metaKey: 0,
		ctrlKey: 0,
		shiftKey: 0,
		getModifierState: Rn
	})), Hn = yn(f({}, bn, {
		propertyName: 0,
		elapsedTime: 0,
		pseudoElement: 0
	})), Un = yn(f({}, Dn, {
		deltaX: function(e) {
			return "deltaX" in e ? e.deltaX : "wheelDeltaX" in e ? -e.wheelDeltaX : 0;
		},
		deltaY: function(e) {
			return "deltaY" in e ? e.deltaY : "wheelDeltaY" in e ? -e.wheelDeltaY : "wheelDelta" in e ? -e.wheelDelta : 0;
		},
		deltaZ: 0,
		deltaMode: 0
	})), Wn = yn(f({}, bn, {
		newState: 0,
		oldState: 0
	})), Gn = [
		9,
		13,
		27,
		32
	], Kn = ln && "CompositionEvent" in window, qn = null;
	ln && "documentMode" in document && (qn = document.documentMode);
	var Jn = ln && "TextEvent" in window && !qn, Yn = ln && (!Kn || qn && 8 < qn && 11 >= qn), Xn = " ", Zn = !1;
	function Qn(e, t) {
		switch (e) {
			case "keyup": return Gn.indexOf(t.keyCode) !== -1;
			case "keydown": return t.keyCode !== 229;
			case "keypress":
			case "mousedown":
			case "focusout": return !0;
			default: return !1;
		}
	}
	function $n(e) {
		return e = e.detail, typeof e == "object" && "data" in e ? e.data : null;
	}
	var er = !1;
	function tr(e, t) {
		switch (e) {
			case "compositionend": return $n(t);
			case "keypress": return t.which === 32 ? (Zn = !0, Xn) : null;
			case "textInput": return e = t.data, e === Xn && Zn ? null : e;
			default: return null;
		}
	}
	function nr(e, t) {
		if (er) return e === "compositionend" || !Kn && Qn(e, t) ? (e = hn(), mn = pn = fn = null, er = !1, e) : null;
		switch (e) {
			case "paste": return null;
			case "keypress":
				if (!(t.ctrlKey || t.altKey || t.metaKey) || t.ctrlKey && t.altKey) {
					if (t.char && 1 < t.char.length) return t.char;
					if (t.which) return String.fromCharCode(t.which);
				}
				return null;
			case "compositionend": return Yn && t.locale !== "ko" ? null : t.data;
			default: return null;
		}
	}
	var rr = {
		color: !0,
		date: !0,
		datetime: !0,
		"datetime-local": !0,
		email: !0,
		month: !0,
		number: !0,
		password: !0,
		range: !0,
		search: !0,
		tel: !0,
		text: !0,
		time: !0,
		url: !0,
		week: !0
	};
	function ir(e) {
		var t = e && e.nodeName && e.nodeName.toLowerCase();
		return t === "input" ? !!rr[e.type] : t === "textarea";
	}
	function ar(e, t, n, r) {
		nn ? rn ? rn.push(r) : rn = [r] : nn = r, t = kd(t, "onChange"), 0 < t.length && (n = new xn("onChange", "change", null, n, r), e.push({
			event: n,
			listeners: t
		}));
	}
	var or = null, sr = null;
	function cr(e) {
		J(e, 0);
	}
	function lr(e) {
		if (Ft(_t(e))) return e;
	}
	function ur(e, t) {
		if (e === "change") return t;
	}
	var dr = !1;
	if (ln) {
		var fr;
		if (ln) {
			var pr = "oninput" in document;
			if (!pr) {
				var mr = document.createElement("div");
				mr.setAttribute("oninput", "return;"), pr = typeof mr.oninput == "function";
			}
			fr = pr;
		} else fr = !1;
		dr = fr && (!document.documentMode || 9 < document.documentMode);
	}
	function hr() {
		or && (or.detachEvent("onpropertychange", gr), sr = or = null);
	}
	function gr(e) {
		if (e.propertyName === "value" && lr(sr)) {
			var t = [];
			ar(t, sr, e, tn(e)), sn(cr, t);
		}
	}
	function _r(e, t, n) {
		e === "focusin" ? (hr(), or = t, sr = n, or.attachEvent("onpropertychange", gr)) : e === "focusout" && hr();
	}
	function vr(e) {
		if (e === "selectionchange" || e === "keyup" || e === "keydown") return lr(sr);
	}
	function yr(e, t) {
		if (e === "click") return lr(t);
	}
	function br(e, t) {
		if (e === "input" || e === "change") return lr(t);
	}
	function xr(e, t) {
		return e === t && (e !== 0 || 1 / e == 1 / t) || e !== e && t !== t;
	}
	var Sr = typeof Object.is == "function" ? Object.is : xr;
	function Cr(e, t) {
		if (Sr(e, t)) return !0;
		if (typeof e != "object" || !e || typeof t != "object" || !t) return !1;
		var n = Object.keys(e), r = Object.keys(t);
		if (n.length !== r.length) return !1;
		for (r = 0; r < n.length; r++) {
			var i = n[r];
			if (!L.call(t, i) || !Sr(e[i], t[i])) return !1;
		}
		return !0;
	}
	function wr(e) {
		for (; e && e.firstChild;) e = e.firstChild;
		return e;
	}
	function Tr(e, t) {
		var n = wr(e);
		e = 0;
		for (var r; n;) {
			if (n.nodeType === 3) {
				if (r = e + n.textContent.length, e <= t && r >= t) return {
					node: n,
					offset: t - e
				};
				e = r;
			}
			a: {
				for (; n;) {
					if (n.nextSibling) {
						n = n.nextSibling;
						break a;
					}
					n = n.parentNode;
				}
				n = void 0;
			}
			n = wr(n);
		}
	}
	function Er(e, t) {
		return e && t ? e === t ? !0 : e && e.nodeType === 3 ? !1 : t && t.nodeType === 3 ? Er(e, t.parentNode) : "contains" in e ? e.contains(t) : e.compareDocumentPosition ? !!(e.compareDocumentPosition(t) & 16) : !1 : !1;
	}
	function Dr(e) {
		e = e != null && e.ownerDocument != null && e.ownerDocument.defaultView != null ? e.ownerDocument.defaultView : window;
		for (var t = It(e.document); t instanceof e.HTMLIFrameElement;) {
			try {
				var n = typeof t.contentWindow.location.href == "string";
			} catch {
				n = !1;
			}
			if (n) e = t.contentWindow;
			else break;
			t = It(e.document);
		}
		return t;
	}
	function Or(e) {
		var t = e && e.nodeName && e.nodeName.toLowerCase();
		return t && (t === "input" && (e.type === "text" || e.type === "search" || e.type === "tel" || e.type === "url" || e.type === "password") || t === "textarea" || e.contentEditable === "true");
	}
	var kr = ln && "documentMode" in document && 11 >= document.documentMode, Ar = null, jr = null, Mr = null, Nr = !1;
	function Pr(e, t, n) {
		var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
		Nr || Ar == null || Ar !== It(r) || (r = Ar, "selectionStart" in r && Or(r) ? r = {
			start: r.selectionStart,
			end: r.selectionEnd
		} : (r = (r.ownerDocument && r.ownerDocument.defaultView || window).getSelection(), r = {
			anchorNode: r.anchorNode,
			anchorOffset: r.anchorOffset,
			focusNode: r.focusNode,
			focusOffset: r.focusOffset
		}), Mr && Cr(Mr, r) || (Mr = r, r = kd(jr, "onSelect"), 0 < r.length && (t = new xn("onSelect", "select", null, t, n), e.push({
			event: t,
			listeners: r
		}), t.target = Ar)));
	}
	function Fr(e, t) {
		var n = {};
		return n[e.toLowerCase()] = t.toLowerCase(), n["Webkit" + e] = "webkit" + t, n["Moz" + e] = "moz" + t, n;
	}
	var Ir = {
		animationend: Fr("Animation", "AnimationEnd"),
		animationiteration: Fr("Animation", "AnimationIteration"),
		animationstart: Fr("Animation", "AnimationStart"),
		transitionrun: Fr("Transition", "TransitionRun"),
		transitionstart: Fr("Transition", "TransitionStart"),
		transitioncancel: Fr("Transition", "TransitionCancel"),
		transitionend: Fr("Transition", "TransitionEnd")
	}, Lr = {}, Rr = {};
	ln && (Rr = document.createElement("div").style, "AnimationEvent" in window || (delete Ir.animationend.animation, delete Ir.animationiteration.animation, delete Ir.animationstart.animation), "TransitionEvent" in window || delete Ir.transitionend.transition);
	function zr(e) {
		if (Lr[e]) return Lr[e];
		if (!Ir[e]) return e;
		var t = Ir[e], n;
		for (n in t) if (t.hasOwnProperty(n) && n in Rr) return Lr[e] = t[n];
		return e;
	}
	var Br = zr("animationend"), Vr = zr("animationiteration"), Hr = zr("animationstart"), Ur = zr("transitionrun"), Wr = zr("transitionstart"), Gr = zr("transitioncancel"), Kr = zr("transitionend"), qr = /* @__PURE__ */ new Map(), Jr = "abort auxClick beforeToggle cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");
	Jr.push("scrollEnd");
	function Yr(e, t) {
		qr.set(e, t), St(t, [e]);
	}
	var Xr = typeof reportError == "function" ? reportError : function(e) {
		if (typeof window == "object" && typeof window.ErrorEvent == "function") {
			var t = new window.ErrorEvent("error", {
				bubbles: !0,
				cancelable: !0,
				message: typeof e == "object" && e && typeof e.message == "string" ? String(e.message) : String(e),
				error: e
			});
			if (!window.dispatchEvent(t)) return;
		} else if (typeof process == "object" && typeof process.emit == "function") {
			process.emit("uncaughtException", e);
			return;
		}
		console.error(e);
	}, Zr = [], Qr = 0, $r = 0;
	function ei() {
		for (var e = Qr, t = $r = Qr = 0; t < e;) {
			var n = Zr[t];
			Zr[t++] = null;
			var r = Zr[t];
			Zr[t++] = null;
			var i = Zr[t];
			Zr[t++] = null;
			var a = Zr[t];
			if (Zr[t++] = null, r !== null && i !== null) {
				var o = r.pending;
				o === null ? i.next = i : (i.next = o.next, o.next = i), r.pending = i;
			}
			a !== 0 && ii(n, i, a);
		}
	}
	function ti(e, t, n, r) {
		Zr[Qr++] = e, Zr[Qr++] = t, Zr[Qr++] = n, Zr[Qr++] = r, $r |= r, e.lanes |= r, e = e.alternate, e !== null && (e.lanes |= r);
	}
	function ni(e, t, n, r) {
		return ti(e, t, n, r), ai(e);
	}
	function ri(e, t) {
		return ti(e, null, null, t), ai(e);
	}
	function ii(e, t, n) {
		e.lanes |= n;
		var r = e.alternate;
		r !== null && (r.lanes |= n);
		for (var i = !1, a = e.return; a !== null;) a.childLanes |= n, r = a.alternate, r !== null && (r.childLanes |= n), a.tag === 22 && (e = a.stateNode, e === null || e._visibility & 1 || (i = !0)), e = a, a = a.return;
		return e.tag === 3 ? (a = e.stateNode, i && t !== null && (i = 31 - Re(n), e = a.hiddenUpdates, r = e[i], r === null ? e[i] = [t] : r.push(t), t.lane = n | 536870912), a) : null;
	}
	function ai(e) {
		if (50 < mu) throw mu = 0, hu = null, Error(i(185));
		for (var t = e.return; t !== null;) e = t, t = e.return;
		return e.tag === 3 ? e.stateNode : null;
	}
	var oi = {};
	function si(e, t, n, r) {
		this.tag = e, this.key = n, this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null, this.index = 0, this.refCleanup = this.ref = null, this.pendingProps = t, this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null, this.mode = r, this.subtreeFlags = this.flags = 0, this.deletions = null, this.childLanes = this.lanes = 0, this.alternate = null;
	}
	function ci(e, t, n, r) {
		return new si(e, t, n, r);
	}
	function li(e) {
		return e = e.prototype, !(!e || !e.isReactComponent);
	}
	function ui(e, t) {
		var n = e.alternate;
		return n === null ? (n = ci(e.tag, t, e.key, e.mode), n.elementType = e.elementType, n.type = e.type, n.stateNode = e.stateNode, n.alternate = e, e.alternate = n) : (n.pendingProps = t, n.type = e.type, n.flags = 0, n.subtreeFlags = 0, n.deletions = null), n.flags = e.flags & 65011712, n.childLanes = e.childLanes, n.lanes = e.lanes, n.child = e.child, n.memoizedProps = e.memoizedProps, n.memoizedState = e.memoizedState, n.updateQueue = e.updateQueue, t = e.dependencies, n.dependencies = t === null ? null : {
			lanes: t.lanes,
			firstContext: t.firstContext
		}, n.sibling = e.sibling, n.index = e.index, n.ref = e.ref, n.refCleanup = e.refCleanup, n;
	}
	function di(e, t) {
		e.flags &= 65011714;
		var n = e.alternate;
		return n === null ? (e.childLanes = 0, e.lanes = t, e.child = null, e.subtreeFlags = 0, e.memoizedProps = null, e.memoizedState = null, e.updateQueue = null, e.dependencies = null, e.stateNode = null) : (e.childLanes = n.childLanes, e.lanes = n.lanes, e.child = n.child, e.subtreeFlags = 0, e.deletions = null, e.memoizedProps = n.memoizedProps, e.memoizedState = n.memoizedState, e.updateQueue = n.updateQueue, e.type = n.type, t = n.dependencies, e.dependencies = t === null ? null : {
			lanes: t.lanes,
			firstContext: t.firstContext
		}), e;
	}
	function fi(e, t, n, r, a, o) {
		var s = 0;
		if (r = e, typeof e == "function") li(e) && (s = 1);
		else if (typeof e == "string") s = qf(e, n, ae.current) ? 26 : e === "html" || e === "head" || e === "body" ? 27 : 5;
		else a: switch (e) {
			case E: return e = ci(31, n, t, a), e.elementType = E, e.lanes = o, e;
			case g: return pi(n.children, a, o, t);
			case _:
				s = 8, a |= 24;
				break;
			case v: return e = ci(12, n, t, a | 2), e.elementType = v, e.lanes = o, e;
			case S: return e = ci(13, n, t, a), e.elementType = S, e.lanes = o, e;
			case C: return e = ci(19, n, t, a), e.elementType = C, e.lanes = o, e;
			default:
				if (typeof e == "object" && e) switch (e.$$typeof) {
					case b:
						s = 10;
						break a;
					case y:
						s = 9;
						break a;
					case x:
						s = 11;
						break a;
					case w:
						s = 14;
						break a;
					case T:
						s = 16, r = null;
						break a;
				}
				s = 29, n = Error(i(130, e === null ? "null" : typeof e, "")), r = null;
		}
		return t = ci(s, n, t, a), t.elementType = e, t.type = r, t.lanes = o, t;
	}
	function pi(e, t, n, r) {
		return e = ci(7, e, r, t), e.lanes = n, e;
	}
	function mi(e, t, n) {
		return e = ci(6, e, null, t), e.lanes = n, e;
	}
	function hi(e) {
		var t = ci(18, null, null, 0);
		return t.stateNode = e, t;
	}
	function gi(e, t, n) {
		return t = ci(4, e.children === null ? [] : e.children, e.key, t), t.lanes = n, t.stateNode = {
			containerInfo: e.containerInfo,
			pendingChildren: null,
			implementation: e.implementation
		}, t;
	}
	var _i = /* @__PURE__ */ new WeakMap();
	function vi(e, t) {
		if (typeof e == "object" && e) {
			var n = _i.get(e);
			return n === void 0 ? (t = {
				value: e,
				source: t,
				stack: xe(t)
			}, _i.set(e, t), t) : n;
		}
		return {
			value: e,
			source: t,
			stack: xe(t)
		};
	}
	var yi = [], bi = 0, xi = null, Si = 0, Ci = [], wi = 0, Ti = null, Ei = 1, Di = "";
	function Oi(e, t) {
		yi[bi++] = Si, yi[bi++] = xi, xi = e, Si = t;
	}
	function ki(e, t, n) {
		Ci[wi++] = Ei, Ci[wi++] = Di, Ci[wi++] = Ti, Ti = e;
		var r = Ei;
		e = Di;
		var i = 32 - Re(r) - 1;
		r &= ~(1 << i), n += 1;
		var a = 32 - Re(t) + i;
		if (30 < a) {
			var o = i - i % 5;
			a = (r & (1 << o) - 1).toString(32), r >>= o, i -= o, Ei = 1 << 32 - Re(t) + i | n << i | r, Di = a + e;
		} else Ei = 1 << a | n << i | r, Di = e;
	}
	function Ai(e) {
		e.return !== null && (Oi(e, 1), ki(e, 1, 0));
	}
	function ji(e) {
		for (; e === xi;) xi = yi[--bi], yi[bi] = null, Si = yi[--bi], yi[bi] = null;
		for (; e === Ti;) Ti = Ci[--wi], Ci[wi] = null, Di = Ci[--wi], Ci[wi] = null, Ei = Ci[--wi], Ci[wi] = null;
	}
	function Mi(e, t) {
		Ci[wi++] = Ei, Ci[wi++] = Di, Ci[wi++] = Ti, Ei = t.id, Di = t.overflow, Ti = e;
	}
	var Ni = null, Pi = null, z = !1, Fi = null, Ii = !1, Li = Error(i(519));
	function Ri(e) {
		throw Wi(vi(Error(i(418, 1 < arguments.length && arguments[1] !== void 0 && arguments[1] ? "text" : "HTML", "")), e)), Li;
	}
	function zi(e) {
		var t = e.stateNode, n = e.type, r = e.memoizedProps;
		switch (t[ot] = e, t[st] = r, n) {
			case "dialog":
				Y("cancel", t), Y("close", t);
				break;
			case "iframe":
			case "object":
			case "embed":
				Y("load", t);
				break;
			case "video":
			case "audio":
				for (n = 0; n < xd.length; n++) Y(xd[n], t);
				break;
			case "source":
				Y("error", t);
				break;
			case "img":
			case "image":
			case "link":
				Y("error", t), Y("load", t);
				break;
			case "details":
				Y("toggle", t);
				break;
			case "input":
				Y("invalid", t), Bt(t, r.value, r.defaultValue, r.checked, r.defaultChecked, r.type, r.name, !0);
				break;
			case "select":
				Y("invalid", t);
				break;
			case "textarea": Y("invalid", t), Wt(t, r.value, r.defaultValue, r.children);
		}
		n = r.children, typeof n != "string" && typeof n != "number" && typeof n != "bigint" || t.textContent === "" + n || !0 === r.suppressHydrationWarning || Fd(t.textContent, n) ? (r.popover != null && (Y("beforetoggle", t), Y("toggle", t)), r.onScroll != null && Y("scroll", t), r.onScrollEnd != null && Y("scrollend", t), r.onClick != null && (t.onclick = $t), t = !0) : t = !1, t || Ri(e, !0);
	}
	function Bi(e) {
		for (Ni = e.return; Ni;) switch (Ni.tag) {
			case 5:
			case 31:
			case 13:
				Ii = !1;
				return;
			case 27:
			case 3:
				Ii = !0;
				return;
			default: Ni = Ni.return;
		}
	}
	function Vi(e) {
		if (e !== Ni) return !1;
		if (!z) return Bi(e), z = !0, !1;
		var t = e.tag, n;
		if ((n = t !== 3 && t !== 27) && ((n = t === 5) && (n = e.type, n = !(n !== "form" && n !== "button") || qd(e.type, e.memoizedProps)), n = !n), n && Pi && Ri(e), Bi(e), t === 13) {
			if (e = e.memoizedState, e = e === null ? null : e.dehydrated, !e) throw Error(i(317));
			Pi = mf(e);
		} else if (t === 31) {
			if (e = e.memoizedState, e = e === null ? null : e.dehydrated, !e) throw Error(i(317));
			Pi = mf(e);
		} else t === 27 ? (t = Pi, tf(e.type) ? (e = pf, pf = null, Pi = e) : Pi = t) : Pi = Ni ? ff(e.stateNode.nextSibling) : null;
		return !0;
	}
	function Hi() {
		Pi = Ni = null, z = !1;
	}
	function Ui() {
		var e = Fi;
		return e !== null && (eu === null ? eu = e : eu.push.apply(eu, e), Fi = null), e;
	}
	function Wi(e) {
		Fi === null ? Fi = [e] : Fi.push(e);
	}
	var Gi = re(null), Ki = null, qi = null;
	function Ji(e, t, n) {
		F(Gi, t._currentValue), t._currentValue = n;
	}
	function Yi(e) {
		e._currentValue = Gi.current, ie(Gi);
	}
	function Xi(e, t, n) {
		for (; e !== null;) {
			var r = e.alternate;
			if ((e.childLanes & t) === t ? r !== null && (r.childLanes & t) !== t && (r.childLanes |= t) : (e.childLanes |= t, r !== null && (r.childLanes |= t)), e === n) break;
			e = e.return;
		}
	}
	function Zi(e, t, n, r) {
		var a = e.child;
		for (a !== null && (a.return = e); a !== null;) {
			var o = a.dependencies;
			if (o !== null) {
				var s = a.child;
				o = o.firstContext;
				a: for (; o !== null;) {
					var c = o;
					o = a;
					for (var l = 0; l < t.length; l++) if (c.context === t[l]) {
						o.lanes |= n, c = o.alternate, c !== null && (c.lanes |= n), Xi(o.return, n, e), r || (s = null);
						break a;
					}
					o = c.next;
				}
			} else if (a.tag === 18) {
				if (s = a.return, s === null) throw Error(i(341));
				s.lanes |= n, o = s.alternate, o !== null && (o.lanes |= n), Xi(s, n, e), s = null;
			} else s = a.child;
			if (s !== null) s.return = a;
			else for (s = a; s !== null;) {
				if (s === e) {
					s = null;
					break;
				}
				if (a = s.sibling, a !== null) {
					a.return = s.return, s = a;
					break;
				}
				s = s.return;
			}
			a = s;
		}
	}
	function Qi(e, t, n, r) {
		e = null;
		for (var a = t, o = !1; a !== null;) {
			if (!o) {
				if (a.flags & 524288) o = !0;
				else if (a.flags & 262144) break;
			}
			if (a.tag === 10) {
				var s = a.alternate;
				if (s === null) throw Error(i(387));
				if (s = s.memoizedProps, s !== null) {
					var c = a.type;
					Sr(a.pendingProps.value, s.value) || (e === null ? e = [c] : e.push(c));
				}
			} else if (a === ce.current) {
				if (s = a.alternate, s === null) throw Error(i(387));
				s.memoizedState.memoizedState !== a.memoizedState.memoizedState && (e === null ? e = [np] : e.push(np));
			}
			a = a.return;
		}
		e !== null && Zi(t, e, n, r), t.flags |= 262144;
	}
	function $i(e) {
		for (e = e.firstContext; e !== null;) {
			if (!Sr(e.context._currentValue, e.memoizedValue)) return !0;
			e = e.next;
		}
		return !1;
	}
	function ea(e) {
		Ki = e, qi = null, e = e.dependencies, e !== null && (e.firstContext = null);
	}
	function ta(e) {
		return ra(Ki, e);
	}
	function na(e, t) {
		return Ki === null && ea(e), ra(e, t);
	}
	function ra(e, t) {
		var n = t._currentValue;
		if (t = {
			context: t,
			memoizedValue: n,
			next: null
		}, qi === null) {
			if (e === null) throw Error(i(308));
			qi = t, e.dependencies = {
				lanes: 0,
				firstContext: t
			}, e.flags |= 524288;
		} else qi = qi.next = t;
		return n;
	}
	var ia = typeof AbortController < "u" ? AbortController : function() {
		var e = [], t = this.signal = {
			aborted: !1,
			addEventListener: function(t, n) {
				e.push(n);
			}
		};
		this.abort = function() {
			t.aborted = !0, e.forEach(function(e) {
				return e();
			});
		};
	}, aa = t.unstable_scheduleCallback, oa = t.unstable_NormalPriority, sa = {
		$$typeof: b,
		Consumer: null,
		Provider: null,
		_currentValue: null,
		_currentValue2: null,
		_threadCount: 0
	};
	function ca() {
		return {
			controller: new ia(),
			data: /* @__PURE__ */ new Map(),
			refCount: 0
		};
	}
	function la(e) {
		e.refCount--, e.refCount === 0 && aa(oa, function() {
			e.controller.abort();
		});
	}
	var B = null, ua = 0, da = 0, V = null;
	function fa(e, t) {
		if (B === null) {
			var n = B = [];
			ua = 0, da = hd(), V = {
				status: "pending",
				value: void 0,
				then: function(e) {
					n.push(e);
				}
			};
		}
		return ua++, t.then(pa, pa), t;
	}
	function pa() {
		if (--ua === 0 && B !== null) {
			V !== null && (V.status = "fulfilled");
			var e = B;
			B = null, da = 0, V = null;
			for (var t = 0; t < e.length; t++) (0, e[t])();
		}
	}
	function ma(e, t) {
		var n = [], r = {
			status: "pending",
			value: null,
			reason: null,
			then: function(e) {
				n.push(e);
			}
		};
		return e.then(function() {
			r.status = "fulfilled", r.value = t;
			for (var e = 0; e < n.length; e++) (0, n[e])(t);
		}, function(e) {
			for (r.status = "rejected", r.reason = e, e = 0; e < n.length; e++) (0, n[e])(void 0);
		}), r;
	}
	var ha = M.S;
	M.S = function(e, t) {
		ru = Ee(), typeof t == "object" && t && typeof t.then == "function" && fa(e, t), ha !== null && ha(e, t);
	};
	var ga = re(null);
	function _a() {
		var e = ga.current;
		return e === null ? Bl.pooledCache : e;
	}
	function va(e, t) {
		t === null ? F(ga, ga.current) : F(ga, t.pool);
	}
	function ya() {
		var e = _a();
		return e === null ? null : {
			parent: sa._currentValue,
			pool: e
		};
	}
	var ba = Error(i(460)), xa = Error(i(474)), Sa = Error(i(542)), Ca = { then: function() {} };
	function wa(e) {
		return e = e.status, e === "fulfilled" || e === "rejected";
	}
	function Ta(e, t, n) {
		switch (n = e[n], n === void 0 ? e.push(t) : n !== t && (t.then($t, $t), t = n), t.status) {
			case "fulfilled": return t.value;
			case "rejected": throw e = t.reason, ka(e), e;
			default:
				if (typeof t.status == "string") t.then($t, $t);
				else {
					if (e = Bl, e !== null && 100 < e.shellSuspendCounter) throw Error(i(482));
					e = t, e.status = "pending", e.then(function(e) {
						if (t.status === "pending") {
							var n = t;
							n.status = "fulfilled", n.value = e;
						}
					}, function(e) {
						if (t.status === "pending") {
							var n = t;
							n.status = "rejected", n.reason = e;
						}
					});
				}
				switch (t.status) {
					case "fulfilled": return t.value;
					case "rejected": throw e = t.reason, ka(e), e;
				}
				throw Da = t, ba;
		}
	}
	function Ea(e) {
		try {
			var t = e._init;
			return t(e._payload);
		} catch (e) {
			throw typeof e == "object" && e && typeof e.then == "function" ? (Da = e, ba) : e;
		}
	}
	var Da = null;
	function Oa() {
		if (Da === null) throw Error(i(459));
		var e = Da;
		return Da = null, e;
	}
	function ka(e) {
		if (e === ba || e === Sa) throw Error(i(483));
	}
	var Aa = null, ja = 0;
	function Ma(e) {
		var t = ja;
		return ja += 1, Aa === null && (Aa = []), Ta(Aa, e, t);
	}
	function Na(e, t) {
		t = t.props.ref, e.ref = t === void 0 ? null : t;
	}
	function Pa(e, t) {
		throw t.$$typeof === p ? Error(i(525)) : (e = Object.prototype.toString.call(t), Error(i(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e)));
	}
	function Fa(e) {
		function t(t, n) {
			if (e) {
				var r = t.deletions;
				r === null ? (t.deletions = [n], t.flags |= 16) : r.push(n);
			}
		}
		function n(n, r) {
			if (!e) return null;
			for (; r !== null;) t(n, r), r = r.sibling;
			return null;
		}
		function r(e) {
			for (var t = /* @__PURE__ */ new Map(); e !== null;) e.key === null ? t.set(e.index, e) : t.set(e.key, e), e = e.sibling;
			return t;
		}
		function a(e, t) {
			return e = ui(e, t), e.index = 0, e.sibling = null, e;
		}
		function o(t, n, r) {
			return t.index = r, e ? (r = t.alternate, r === null ? (t.flags |= 67108866, n) : (r = r.index, r < n ? (t.flags |= 67108866, n) : r)) : (t.flags |= 1048576, n);
		}
		function s(t) {
			return e && t.alternate === null && (t.flags |= 67108866), t;
		}
		function c(e, t, n, r) {
			return t === null || t.tag !== 6 ? (t = mi(n, e.mode, r), t.return = e, t) : (t = a(t, n), t.return = e, t);
		}
		function l(e, t, n, r) {
			var i = n.type;
			return i === g ? d(e, t, n.props.children, r, n.key) : t !== null && (t.elementType === i || typeof i == "object" && i && i.$$typeof === T && Ea(i) === t.type) ? (t = a(t, n.props), Na(t, n), t.return = e, t) : (t = fi(n.type, n.key, n.props, null, e.mode, r), Na(t, n), t.return = e, t);
		}
		function u(e, t, n, r) {
			return t === null || t.tag !== 4 || t.stateNode.containerInfo !== n.containerInfo || t.stateNode.implementation !== n.implementation ? (t = gi(n, e.mode, r), t.return = e, t) : (t = a(t, n.children || []), t.return = e, t);
		}
		function d(e, t, n, r, i) {
			return t === null || t.tag !== 7 ? (t = pi(n, e.mode, r, i), t.return = e, t) : (t = a(t, n), t.return = e, t);
		}
		function f(e, t, n) {
			if (typeof t == "string" && t !== "" || typeof t == "number" || typeof t == "bigint") return t = mi("" + t, e.mode, n), t.return = e, t;
			if (typeof t == "object" && t) {
				switch (t.$$typeof) {
					case m: return n = fi(t.type, t.key, t.props, null, e.mode, n), Na(n, t), n.return = e, n;
					case h: return t = gi(t, e.mode, n), t.return = e, t;
					case T: return t = Ea(t), f(e, t, n);
				}
				if (j(t) || k(t)) return t = pi(t, e.mode, n, null), t.return = e, t;
				if (typeof t.then == "function") return f(e, Ma(t), n);
				if (t.$$typeof === b) return f(e, na(e, t), n);
				Pa(e, t);
			}
			return null;
		}
		function p(e, t, n, r) {
			var i = t === null ? null : t.key;
			if (typeof n == "string" && n !== "" || typeof n == "number" || typeof n == "bigint") return i === null ? c(e, t, "" + n, r) : null;
			if (typeof n == "object" && n) {
				switch (n.$$typeof) {
					case m: return n.key === i ? l(e, t, n, r) : null;
					case h: return n.key === i ? u(e, t, n, r) : null;
					case T: return n = Ea(n), p(e, t, n, r);
				}
				if (j(n) || k(n)) return i === null ? d(e, t, n, r, null) : null;
				if (typeof n.then == "function") return p(e, t, Ma(n), r);
				if (n.$$typeof === b) return p(e, t, na(e, n), r);
				Pa(e, n);
			}
			return null;
		}
		function _(e, t, n, r, i) {
			if (typeof r == "string" && r !== "" || typeof r == "number" || typeof r == "bigint") return e = e.get(n) || null, c(t, e, "" + r, i);
			if (typeof r == "object" && r) {
				switch (r.$$typeof) {
					case m: return e = e.get(r.key === null ? n : r.key) || null, l(t, e, r, i);
					case h: return e = e.get(r.key === null ? n : r.key) || null, u(t, e, r, i);
					case T: return r = Ea(r), _(e, t, n, r, i);
				}
				if (j(r) || k(r)) return e = e.get(n) || null, d(t, e, r, i, null);
				if (typeof r.then == "function") return _(e, t, n, Ma(r), i);
				if (r.$$typeof === b) return _(e, t, n, na(t, r), i);
				Pa(t, r);
			}
			return null;
		}
		function v(i, a, s, c) {
			for (var l = null, u = null, d = a, m = a = 0, h = null; d !== null && m < s.length; m++) {
				d.index > m ? (h = d, d = null) : h = d.sibling;
				var g = p(i, d, s[m], c);
				if (g === null) {
					d === null && (d = h);
					break;
				}
				e && d && g.alternate === null && t(i, d), a = o(g, a, m), u === null ? l = g : u.sibling = g, u = g, d = h;
			}
			if (m === s.length) return n(i, d), z && Oi(i, m), l;
			if (d === null) {
				for (; m < s.length; m++) d = f(i, s[m], c), d !== null && (a = o(d, a, m), u === null ? l = d : u.sibling = d, u = d);
				return z && Oi(i, m), l;
			}
			for (d = r(d); m < s.length; m++) h = _(d, i, m, s[m], c), h !== null && (e && h.alternate !== null && d.delete(h.key === null ? m : h.key), a = o(h, a, m), u === null ? l = h : u.sibling = h, u = h);
			return e && d.forEach(function(e) {
				return t(i, e);
			}), z && Oi(i, m), l;
		}
		function y(a, s, c, l) {
			if (c == null) throw Error(i(151));
			for (var u = null, d = null, m = s, h = s = 0, g = null, v = c.next(); m !== null && !v.done; h++, v = c.next()) {
				m.index > h ? (g = m, m = null) : g = m.sibling;
				var y = p(a, m, v.value, l);
				if (y === null) {
					m === null && (m = g);
					break;
				}
				e && m && y.alternate === null && t(a, m), s = o(y, s, h), d === null ? u = y : d.sibling = y, d = y, m = g;
			}
			if (v.done) return n(a, m), z && Oi(a, h), u;
			if (m === null) {
				for (; !v.done; h++, v = c.next()) v = f(a, v.value, l), v !== null && (s = o(v, s, h), d === null ? u = v : d.sibling = v, d = v);
				return z && Oi(a, h), u;
			}
			for (m = r(m); !v.done; h++, v = c.next()) v = _(m, a, h, v.value, l), v !== null && (e && v.alternate !== null && m.delete(v.key === null ? h : v.key), s = o(v, s, h), d === null ? u = v : d.sibling = v, d = v);
			return e && m.forEach(function(e) {
				return t(a, e);
			}), z && Oi(a, h), u;
		}
		function x(e, r, o, c) {
			if (typeof o == "object" && o && o.type === g && o.key === null && (o = o.props.children), typeof o == "object" && o) {
				switch (o.$$typeof) {
					case m:
						a: {
							for (var l = o.key; r !== null;) {
								if (r.key === l) {
									if (l = o.type, l === g) {
										if (r.tag === 7) {
											n(e, r.sibling), c = a(r, o.props.children), c.return = e, e = c;
											break a;
										}
									} else if (r.elementType === l || typeof l == "object" && l && l.$$typeof === T && Ea(l) === r.type) {
										n(e, r.sibling), c = a(r, o.props), Na(c, o), c.return = e, e = c;
										break a;
									}
									n(e, r);
									break;
								} else t(e, r);
								r = r.sibling;
							}
							o.type === g ? (c = pi(o.props.children, e.mode, c, o.key), c.return = e, e = c) : (c = fi(o.type, o.key, o.props, null, e.mode, c), Na(c, o), c.return = e, e = c);
						}
						return s(e);
					case h:
						a: {
							for (l = o.key; r !== null;) {
								if (r.key === l) if (r.tag === 4 && r.stateNode.containerInfo === o.containerInfo && r.stateNode.implementation === o.implementation) {
									n(e, r.sibling), c = a(r, o.children || []), c.return = e, e = c;
									break a;
								} else {
									n(e, r);
									break;
								}
								else t(e, r);
								r = r.sibling;
							}
							c = gi(o, e.mode, c), c.return = e, e = c;
						}
						return s(e);
					case T: return o = Ea(o), x(e, r, o, c);
				}
				if (j(o)) return v(e, r, o, c);
				if (k(o)) {
					if (l = k(o), typeof l != "function") throw Error(i(150));
					return o = l.call(o), y(e, r, o, c);
				}
				if (typeof o.then == "function") return x(e, r, Ma(o), c);
				if (o.$$typeof === b) return x(e, r, na(e, o), c);
				Pa(e, o);
			}
			return typeof o == "string" && o !== "" || typeof o == "number" || typeof o == "bigint" ? (o = "" + o, r !== null && r.tag === 6 ? (n(e, r.sibling), c = a(r, o), c.return = e, e = c) : (n(e, r), c = mi(o, e.mode, c), c.return = e, e = c), s(e)) : n(e, r);
		}
		return function(e, t, n, r) {
			try {
				ja = 0;
				var i = x(e, t, n, r);
				return Aa = null, i;
			} catch (t) {
				if (t === ba || t === Sa) throw t;
				var a = ci(29, t, null, e.mode);
				return a.lanes = r, a.return = e, a;
			}
		};
	}
	var Ia = Fa(!0), La = Fa(!1), Ra = !1;
	function za(e) {
		e.updateQueue = {
			baseState: e.memoizedState,
			firstBaseUpdate: null,
			lastBaseUpdate: null,
			shared: {
				pending: null,
				lanes: 0,
				hiddenCallbacks: null
			},
			callbacks: null
		};
	}
	function Ba(e, t) {
		e = e.updateQueue, t.updateQueue === e && (t.updateQueue = {
			baseState: e.baseState,
			firstBaseUpdate: e.firstBaseUpdate,
			lastBaseUpdate: e.lastBaseUpdate,
			shared: e.shared,
			callbacks: null
		});
	}
	function Va(e) {
		return {
			lane: e,
			tag: 0,
			payload: null,
			callback: null,
			next: null
		};
	}
	function Ha(e, t, n) {
		var r = e.updateQueue;
		if (r === null) return null;
		if (r = r.shared, zl & 2) {
			var i = r.pending;
			return i === null ? t.next = t : (t.next = i.next, i.next = t), r.pending = t, t = ai(e), ii(e, null, n), t;
		}
		return ti(e, r, t, n), ai(e);
	}
	function Ua(e, t, n) {
		if (t = t.updateQueue, t !== null && (t = t.shared, n & 4194048)) {
			var r = t.lanes;
			r &= e.pendingLanes, n |= r, t.lanes = n, et(e, n);
		}
	}
	function Wa(e, t) {
		var n = e.updateQueue, r = e.alternate;
		if (r !== null && (r = r.updateQueue, n === r)) {
			var i = null, a = null;
			if (n = n.firstBaseUpdate, n !== null) {
				do {
					var o = {
						lane: n.lane,
						tag: n.tag,
						payload: n.payload,
						callback: null,
						next: null
					};
					a === null ? i = a = o : a = a.next = o, n = n.next;
				} while (n !== null);
				a === null ? i = a = t : a = a.next = t;
			} else i = a = t;
			n = {
				baseState: r.baseState,
				firstBaseUpdate: i,
				lastBaseUpdate: a,
				shared: r.shared,
				callbacks: r.callbacks
			}, e.updateQueue = n;
			return;
		}
		e = n.lastBaseUpdate, e === null ? n.firstBaseUpdate = t : e.next = t, n.lastBaseUpdate = t;
	}
	var Ga = !1;
	function Ka() {
		if (Ga) {
			var e = V;
			if (e !== null) throw e;
		}
	}
	function qa(e, t, n, r) {
		Ga = !1;
		var i = e.updateQueue;
		Ra = !1;
		var a = i.firstBaseUpdate, o = i.lastBaseUpdate, s = i.shared.pending;
		if (s !== null) {
			i.shared.pending = null;
			var c = s, l = c.next;
			c.next = null, o === null ? a = l : o.next = l, o = c;
			var u = e.alternate;
			u !== null && (u = u.updateQueue, s = u.lastBaseUpdate, s !== o && (s === null ? u.firstBaseUpdate = l : s.next = l, u.lastBaseUpdate = c));
		}
		if (a !== null) {
			var d = i.baseState;
			o = 0, u = l = c = null, s = a;
			do {
				var p = s.lane & -536870913, m = p !== s.lane;
				if (m ? (q & p) === p : (r & p) === p) {
					p !== 0 && p === da && (Ga = !0), u !== null && (u = u.next = {
						lane: 0,
						tag: s.tag,
						payload: s.payload,
						callback: null,
						next: null
					});
					a: {
						var h = e, g = s;
						p = t;
						var _ = n;
						switch (g.tag) {
							case 1:
								if (h = g.payload, typeof h == "function") {
									d = h.call(_, d, p);
									break a;
								}
								d = h;
								break a;
							case 3: h.flags = h.flags & -65537 | 128;
							case 0:
								if (h = g.payload, p = typeof h == "function" ? h.call(_, d, p) : h, p == null) break a;
								d = f({}, d, p);
								break a;
							case 2: Ra = !0;
						}
					}
					p = s.callback, p !== null && (e.flags |= 64, m && (e.flags |= 8192), m = i.callbacks, m === null ? i.callbacks = [p] : m.push(p));
				} else m = {
					lane: p,
					tag: s.tag,
					payload: s.payload,
					callback: s.callback,
					next: null
				}, u === null ? (l = u = m, c = d) : u = u.next = m, o |= p;
				if (s = s.next, s === null) {
					if (s = i.shared.pending, s === null) break;
					m = s, s = m.next, m.next = null, i.lastBaseUpdate = m, i.shared.pending = null;
				}
			} while (1);
			u === null && (c = d), i.baseState = c, i.firstBaseUpdate = l, i.lastBaseUpdate = u, a === null && (i.shared.lanes = 0), Jl |= o, e.lanes = o, e.memoizedState = d;
		}
	}
	function Ja(e, t) {
		if (typeof e != "function") throw Error(i(191, e));
		e.call(t);
	}
	function Ya(e, t) {
		var n = e.callbacks;
		if (n !== null) for (e.callbacks = null, e = 0; e < n.length; e++) Ja(n[e], t);
	}
	var Xa = re(null), Za = re(0);
	function Qa(e, t) {
		e = Kl, F(Za, e), F(Xa, t), Kl = e | t.baseLanes;
	}
	function $a() {
		F(Za, Kl), F(Xa, Xa.current);
	}
	function eo() {
		Kl = Za.current, ie(Xa), ie(Za);
	}
	var to = re(null), no = null;
	function ro(e) {
		var t = e.alternate;
		F(co, co.current & 1), F(to, e), no === null && (t === null || Xa.current !== null || t.memoizedState !== null) && (no = e);
	}
	function io(e) {
		F(co, co.current), F(to, e), no === null && (no = e);
	}
	function ao(e) {
		e.tag === 22 ? (F(co, co.current), F(to, e), no === null && (no = e)) : oo(e);
	}
	function oo() {
		F(co, co.current), F(to, to.current);
	}
	function so(e) {
		ie(to), no === e && (no = null), ie(co);
	}
	var co = re(0);
	function lo(e) {
		for (var t = e; t !== null;) {
			if (t.tag === 13) {
				var n = t.memoizedState;
				if (n !== null && (n = n.dehydrated, n === null || lf(n) || uf(n))) return t;
			} else if (t.tag === 19 && (t.memoizedProps.revealOrder === "forwards" || t.memoizedProps.revealOrder === "backwards" || t.memoizedProps.revealOrder === "unstable_legacy-backwards" || t.memoizedProps.revealOrder === "together")) {
				if (t.flags & 128) return t;
			} else if (t.child !== null) {
				t.child.return = t, t = t.child;
				continue;
			}
			if (t === e) break;
			for (; t.sibling === null;) {
				if (t.return === null || t.return === e) return null;
				t = t.return;
			}
			t.sibling.return = t.return, t = t.sibling;
		}
		return null;
	}
	var uo = 0, H = null, fo = null, po = null, mo = !1, ho = !1, go = !1, _o = 0, vo = 0, yo = null, bo = 0;
	function xo() {
		throw Error(i(321));
	}
	function So(e, t) {
		if (t === null) return !1;
		for (var n = 0; n < t.length && n < e.length; n++) if (!Sr(e[n], t[n])) return !1;
		return !0;
	}
	function Co(e, t, n, r, i, a) {
		return uo = a, H = t, t.memoizedState = null, t.updateQueue = null, t.lanes = 0, M.H = e === null || e.memoizedState === null ? Ls : Rs, go = !1, a = n(r, i), go = !1, ho && (a = To(t, n, r, i)), wo(e), a;
	}
	function wo(e) {
		M.H = Is;
		var t = fo !== null && fo.next !== null;
		if (uo = 0, po = fo = H = null, mo = !1, vo = 0, yo = null, t) throw Error(i(300));
		e === null || tc || (e = e.dependencies, e !== null && $i(e) && (tc = !0));
	}
	function To(e, t, n, r) {
		H = e;
		var a = 0;
		do {
			if (ho && (yo = null), vo = 0, ho = !1, 25 <= a) throw Error(i(301));
			if (a += 1, po = fo = null, e.updateQueue != null) {
				var o = e.updateQueue;
				o.lastEffect = null, o.events = null, o.stores = null, o.memoCache != null && (o.memoCache.index = 0);
			}
			M.H = zs, o = t(n, r);
		} while (ho);
		return o;
	}
	function Eo() {
		var e = M.H, t = e.useState()[0];
		return t = typeof t.then == "function" ? No(t) : t, e = e.useState()[0], (fo === null ? null : fo.memoizedState) !== e && (H.flags |= 1024), t;
	}
	function Do() {
		var e = _o !== 0;
		return _o = 0, e;
	}
	function Oo(e, t, n) {
		t.updateQueue = e.updateQueue, t.flags &= -2053, e.lanes &= ~n;
	}
	function ko(e) {
		if (mo) {
			for (e = e.memoizedState; e !== null;) {
				var t = e.queue;
				t !== null && (t.pending = null), e = e.next;
			}
			mo = !1;
		}
		uo = 0, po = fo = H = null, ho = !1, vo = _o = 0, yo = null;
	}
	function Ao() {
		var e = {
			memoizedState: null,
			baseState: null,
			baseQueue: null,
			queue: null,
			next: null
		};
		return po === null ? H.memoizedState = po = e : po = po.next = e, po;
	}
	function jo() {
		if (fo === null) {
			var e = H.alternate;
			e = e === null ? null : e.memoizedState;
		} else e = fo.next;
		var t = po === null ? H.memoizedState : po.next;
		if (t !== null) po = t, fo = e;
		else {
			if (e === null) throw H.alternate === null ? Error(i(467)) : Error(i(310));
			fo = e, e = {
				memoizedState: fo.memoizedState,
				baseState: fo.baseState,
				baseQueue: fo.baseQueue,
				queue: fo.queue,
				next: null
			}, po === null ? H.memoizedState = po = e : po = po.next = e;
		}
		return po;
	}
	function Mo() {
		return {
			lastEffect: null,
			events: null,
			stores: null,
			memoCache: null
		};
	}
	function No(e) {
		var t = vo;
		return vo += 1, yo === null && (yo = []), e = Ta(yo, e, t), t = H, (po === null ? t.memoizedState : po.next) === null && (t = t.alternate, M.H = t === null || t.memoizedState === null ? Ls : Rs), e;
	}
	function Po(e) {
		if (typeof e == "object" && e) {
			if (typeof e.then == "function") return No(e);
			if (e.$$typeof === b) return ta(e);
		}
		throw Error(i(438, String(e)));
	}
	function Fo(e) {
		var t = null, n = H.updateQueue;
		if (n !== null && (t = n.memoCache), t == null) {
			var r = H.alternate;
			r !== null && (r = r.updateQueue, r !== null && (r = r.memoCache, r != null && (t = {
				data: r.data.map(function(e) {
					return e.slice();
				}),
				index: 0
			})));
		}
		if (t ??= {
			data: [],
			index: 0
		}, n === null && (n = Mo(), H.updateQueue = n), n.memoCache = t, n = t.data[t.index], n === void 0) for (n = t.data[t.index] = Array(e), r = 0; r < e; r++) n[r] = D;
		return t.index++, n;
	}
	function Io(e, t) {
		return typeof t == "function" ? t(e) : t;
	}
	function Lo(e) {
		return Ro(jo(), fo, e);
	}
	function Ro(e, t, n) {
		var r = e.queue;
		if (r === null) throw Error(i(311));
		r.lastRenderedReducer = n;
		var a = e.baseQueue, o = r.pending;
		if (o !== null) {
			if (a !== null) {
				var s = a.next;
				a.next = o.next, o.next = s;
			}
			t.baseQueue = a = o, r.pending = null;
		}
		if (o = e.baseState, a === null) e.memoizedState = o;
		else {
			t = a.next;
			var c = s = null, l = null, u = t, d = !1;
			do {
				var f = u.lane & -536870913;
				if (f === u.lane ? (uo & f) === f : (q & f) === f) {
					var p = u.revertLane;
					if (p === 0) l !== null && (l = l.next = {
						lane: 0,
						revertLane: 0,
						gesture: null,
						action: u.action,
						hasEagerState: u.hasEagerState,
						eagerState: u.eagerState,
						next: null
					}), f === da && (d = !0);
					else if ((uo & p) === p) {
						u = u.next, p === da && (d = !0);
						continue;
					} else f = {
						lane: 0,
						revertLane: u.revertLane,
						gesture: null,
						action: u.action,
						hasEagerState: u.hasEagerState,
						eagerState: u.eagerState,
						next: null
					}, l === null ? (c = l = f, s = o) : l = l.next = f, H.lanes |= p, Jl |= p;
					f = u.action, go && n(o, f), o = u.hasEagerState ? u.eagerState : n(o, f);
				} else p = {
					lane: f,
					revertLane: u.revertLane,
					gesture: u.gesture,
					action: u.action,
					hasEagerState: u.hasEagerState,
					eagerState: u.eagerState,
					next: null
				}, l === null ? (c = l = p, s = o) : l = l.next = p, H.lanes |= f, Jl |= f;
				u = u.next;
			} while (u !== null && u !== t);
			if (l === null ? s = o : l.next = c, !Sr(o, e.memoizedState) && (tc = !0, d && (n = V, n !== null))) throw n;
			e.memoizedState = o, e.baseState = s, e.baseQueue = l, r.lastRenderedState = o;
		}
		return a === null && (r.lanes = 0), [e.memoizedState, r.dispatch];
	}
	function zo(e) {
		var t = jo(), n = t.queue;
		if (n === null) throw Error(i(311));
		n.lastRenderedReducer = e;
		var r = n.dispatch, a = n.pending, o = t.memoizedState;
		if (a !== null) {
			n.pending = null;
			var s = a = a.next;
			do
				o = e(o, s.action), s = s.next;
			while (s !== a);
			Sr(o, t.memoizedState) || (tc = !0), t.memoizedState = o, t.baseQueue === null && (t.baseState = o), n.lastRenderedState = o;
		}
		return [o, r];
	}
	function Bo(e, t, n) {
		var r = H, a = jo(), o = z;
		if (o) {
			if (n === void 0) throw Error(i(407));
			n = n();
		} else n = t();
		var s = !Sr((fo || a).memoizedState, n);
		if (s && (a.memoizedState = n, tc = !0), a = a.queue, cs(Uo.bind(null, r, a, e), [e]), a.getSnapshot !== t || s || po !== null && po.memoizedState.tag & 1) {
			if (r.flags |= 2048, rs(9, { destroy: void 0 }, Ho.bind(null, r, a, n, t), null), Bl === null) throw Error(i(349));
			o || uo & 127 || Vo(r, t, n);
		}
		return n;
	}
	function Vo(e, t, n) {
		e.flags |= 16384, e = {
			getSnapshot: t,
			value: n
		}, t = H.updateQueue, t === null ? (t = Mo(), H.updateQueue = t, t.stores = [e]) : (n = t.stores, n === null ? t.stores = [e] : n.push(e));
	}
	function Ho(e, t, n, r) {
		t.value = n, t.getSnapshot = r, Wo(t) && Go(e);
	}
	function Uo(e, t, n) {
		return n(function() {
			Wo(t) && Go(e);
		});
	}
	function Wo(e) {
		var t = e.getSnapshot;
		e = e.value;
		try {
			var n = t();
			return !Sr(e, n);
		} catch {
			return !0;
		}
	}
	function Go(e) {
		var t = ri(e, 2);
		t !== null && vu(t, e, 2);
	}
	function Ko(e) {
		var t = Ao();
		if (typeof e == "function") {
			var n = e;
			if (e = n(), go) {
				Le(!0);
				try {
					n();
				} finally {
					Le(!1);
				}
			}
		}
		return t.memoizedState = t.baseState = e, t.queue = {
			pending: null,
			lanes: 0,
			dispatch: null,
			lastRenderedReducer: Io,
			lastRenderedState: e
		}, t;
	}
	function qo(e, t, n, r) {
		return e.baseState = n, Ro(e, fo, typeof r == "function" ? r : Io);
	}
	function Jo(e, t, n, r, a) {
		if (Ns(e)) throw Error(i(485));
		if (e = t.action, e !== null) {
			var o = {
				payload: a,
				action: e,
				next: null,
				isTransition: !0,
				status: "pending",
				value: null,
				reason: null,
				listeners: [],
				then: function(e) {
					o.listeners.push(e);
				}
			};
			M.T === null ? o.isTransition = !1 : n(!0), r(o), n = t.pending, n === null ? (o.next = t.pending = o, Yo(t, o)) : (o.next = n.next, t.pending = n.next = o);
		}
	}
	function Yo(e, t) {
		var n = t.action, r = t.payload, i = e.state;
		if (t.isTransition) {
			var a = M.T, o = {};
			M.T = o;
			try {
				var s = n(i, r), c = M.S;
				c !== null && c(o, s), U(e, t, s);
			} catch (n) {
				W(e, t, n);
			} finally {
				a !== null && o.types !== null && (a.types = o.types), M.T = a;
			}
		} else try {
			a = n(i, r), U(e, t, a);
		} catch (n) {
			W(e, t, n);
		}
	}
	function U(e, t, n) {
		typeof n == "object" && n && typeof n.then == "function" ? n.then(function(n) {
			Xo(e, t, n);
		}, function(n) {
			return W(e, t, n);
		}) : Xo(e, t, n);
	}
	function Xo(e, t, n) {
		t.status = "fulfilled", t.value = n, Zo(t), e.state = n, t = e.pending, t !== null && (n = t.next, n === t ? e.pending = null : (n = n.next, t.next = n, Yo(e, n)));
	}
	function W(e, t, n) {
		var r = e.pending;
		if (e.pending = null, r !== null) {
			r = r.next;
			do
				t.status = "rejected", t.reason = n, Zo(t), t = t.next;
			while (t !== r);
		}
		e.action = null;
	}
	function Zo(e) {
		e = e.listeners;
		for (var t = 0; t < e.length; t++) (0, e[t])();
	}
	function Qo(e, t) {
		return t;
	}
	function $o(e, t) {
		if (z) {
			var n = Bl.formState;
			if (n !== null) {
				a: {
					var r = H;
					if (z) {
						if (Pi) {
							b: {
								for (var i = Pi, a = Ii; i.nodeType !== 8;) {
									if (!a) {
										i = null;
										break b;
									}
									if (i = ff(i.nextSibling), i === null) {
										i = null;
										break b;
									}
								}
								a = i.data, i = a === "F!" || a === "F" ? i : null;
							}
							if (i) {
								Pi = ff(i.nextSibling), r = i.data === "F!";
								break a;
							}
						}
						Ri(r);
					}
					r = !1;
				}
				r && (t = n[0]);
			}
		}
		return n = Ao(), n.memoizedState = n.baseState = t, r = {
			pending: null,
			lanes: 0,
			dispatch: null,
			lastRenderedReducer: Qo,
			lastRenderedState: t
		}, n.queue = r, n = As.bind(null, H, r), r.dispatch = n, r = Ko(!1), a = Ms.bind(null, H, !1, r.queue), r = Ao(), i = {
			state: t,
			dispatch: null,
			action: e,
			pending: null
		}, r.queue = i, n = Jo.bind(null, H, i, a, n), i.dispatch = n, r.memoizedState = e, [
			t,
			n,
			!1
		];
	}
	function es(e) {
		return G(jo(), fo, e);
	}
	function G(e, t, n) {
		if (t = Ro(e, t, Qo)[0], e = Lo(Io)[0], typeof t == "object" && t && typeof t.then == "function") try {
			var r = No(t);
		} catch (e) {
			throw e === ba ? Sa : e;
		}
		else r = t;
		t = jo();
		var i = t.queue, a = i.dispatch;
		return n !== t.memoizedState && (H.flags |= 2048, rs(9, { destroy: void 0 }, ts.bind(null, i, n), null)), [
			r,
			a,
			e
		];
	}
	function ts(e, t) {
		e.action = t;
	}
	function ns(e) {
		var t = jo(), n = fo;
		if (n !== null) return G(t, n, e);
		jo(), t = t.memoizedState, n = jo();
		var r = n.queue.dispatch;
		return n.memoizedState = e, [
			t,
			r,
			!1
		];
	}
	function rs(e, t, n, r) {
		return e = {
			tag: e,
			create: n,
			deps: r,
			inst: t,
			next: null
		}, t = H.updateQueue, t === null && (t = Mo(), H.updateQueue = t), n = t.lastEffect, n === null ? t.lastEffect = e.next = e : (r = n.next, n.next = e, e.next = r, t.lastEffect = e), e;
	}
	function is() {
		return jo().memoizedState;
	}
	function as(e, t, n, r) {
		var i = Ao();
		H.flags |= e, i.memoizedState = rs(1 | t, { destroy: void 0 }, n, r === void 0 ? null : r);
	}
	function os(e, t, n, r) {
		var i = jo();
		r = r === void 0 ? null : r;
		var a = i.memoizedState.inst;
		fo !== null && r !== null && So(r, fo.memoizedState.deps) ? i.memoizedState = rs(t, a, n, r) : (H.flags |= e, i.memoizedState = rs(1 | t, a, n, r));
	}
	function ss(e, t) {
		as(8390656, 8, e, t);
	}
	function cs(e, t) {
		os(2048, 8, e, t);
	}
	function ls(e) {
		H.flags |= 4;
		var t = H.updateQueue;
		if (t === null) t = Mo(), H.updateQueue = t, t.events = [e];
		else {
			var n = t.events;
			n === null ? t.events = [e] : n.push(e);
		}
	}
	function us(e) {
		var t = jo().memoizedState;
		return ls({
			ref: t,
			nextImpl: e
		}), function() {
			if (zl & 2) throw Error(i(440));
			return t.impl.apply(void 0, arguments);
		};
	}
	function ds(e, t) {
		return os(4, 2, e, t);
	}
	function fs(e, t) {
		return os(4, 4, e, t);
	}
	function ps(e, t) {
		if (typeof t == "function") {
			e = e();
			var n = t(e);
			return function() {
				typeof n == "function" ? n() : t(null);
			};
		}
		if (t != null) return e = e(), t.current = e, function() {
			t.current = null;
		};
	}
	function ms(e, t, n) {
		n = n == null ? null : n.concat([e]), os(4, 4, ps.bind(null, t, e), n);
	}
	function hs() {}
	function gs(e, t) {
		var n = jo();
		t = t === void 0 ? null : t;
		var r = n.memoizedState;
		return t !== null && So(t, r[1]) ? r[0] : (n.memoizedState = [e, t], e);
	}
	function _s(e, t) {
		var n = jo();
		t = t === void 0 ? null : t;
		var r = n.memoizedState;
		if (t !== null && So(t, r[1])) return r[0];
		if (r = e(), go) {
			Le(!0);
			try {
				e();
			} finally {
				Le(!1);
			}
		}
		return n.memoizedState = [r, t], r;
	}
	function vs(e, t, n) {
		return n === void 0 || uo & 1073741824 && !(q & 261930) ? e.memoizedState = t : (e.memoizedState = n, e = _u(), H.lanes |= e, Jl |= e, n);
	}
	function ys(e, t, n, r) {
		return Sr(n, t) ? n : Xa.current === null ? !(uo & 42) || uo & 1073741824 && !(q & 261930) ? (tc = !0, e.memoizedState = n) : (e = _u(), H.lanes |= e, Jl |= e, t) : (e = vs(e, n, r), Sr(e, t) || (tc = !0), e);
	}
	function bs(e, t, n, r, i) {
		var a = N.p;
		N.p = a !== 0 && 8 > a ? a : 8;
		var o = M.T, s = {};
		M.T = s, Ms(e, !1, t, n);
		try {
			var c = i(), l = M.S;
			l !== null && l(s, c), typeof c == "object" && c && typeof c.then == "function" ? js(e, t, ma(c, r), gu(e)) : js(e, t, r, gu(e));
		} catch (n) {
			js(e, t, {
				then: function() {},
				status: "rejected",
				reason: n
			}, gu());
		} finally {
			N.p = a, o !== null && s.types !== null && (o.types = s.types), M.T = o;
		}
	}
	function xs() {}
	function Ss(e, t, n, r) {
		if (e.tag !== 5) throw Error(i(476));
		var a = Cs(e).queue;
		bs(e, a, t, P, n === null ? xs : function() {
			return ws(e), n(r);
		});
	}
	function Cs(e) {
		var t = e.memoizedState;
		if (t !== null) return t;
		t = {
			memoizedState: P,
			baseState: P,
			baseQueue: null,
			queue: {
				pending: null,
				lanes: 0,
				dispatch: null,
				lastRenderedReducer: Io,
				lastRenderedState: P
			},
			next: null
		};
		var n = {};
		return t.next = {
			memoizedState: n,
			baseState: n,
			baseQueue: null,
			queue: {
				pending: null,
				lanes: 0,
				dispatch: null,
				lastRenderedReducer: Io,
				lastRenderedState: n
			},
			next: null
		}, e.memoizedState = t, e = e.alternate, e !== null && (e.memoizedState = t), t;
	}
	function ws(e) {
		var t = Cs(e);
		t.next === null && (t = e.alternate.memoizedState), js(e, t.next.queue, {}, gu());
	}
	function Ts() {
		return ta(np);
	}
	function Es() {
		return jo().memoizedState;
	}
	function Ds() {
		return jo().memoizedState;
	}
	function Os(e) {
		for (var t = e.return; t !== null;) {
			switch (t.tag) {
				case 24:
				case 3:
					var n = gu();
					e = Va(n);
					var r = Ha(t, e, n);
					r !== null && (vu(r, t, n), Ua(r, t, n)), t = { cache: ca() }, e.payload = t;
					return;
			}
			t = t.return;
		}
	}
	function ks(e, t, n) {
		var r = gu();
		n = {
			lane: r,
			revertLane: 0,
			gesture: null,
			action: n,
			hasEagerState: !1,
			eagerState: null,
			next: null
		}, Ns(e) ? Ps(t, n) : (n = ni(e, t, n, r), n !== null && (vu(n, e, r), Fs(n, t, r)));
	}
	function As(e, t, n) {
		js(e, t, n, gu());
	}
	function js(e, t, n, r) {
		var i = {
			lane: r,
			revertLane: 0,
			gesture: null,
			action: n,
			hasEagerState: !1,
			eagerState: null,
			next: null
		};
		if (Ns(e)) Ps(t, i);
		else {
			var a = e.alternate;
			if (e.lanes === 0 && (a === null || a.lanes === 0) && (a = t.lastRenderedReducer, a !== null)) try {
				var o = t.lastRenderedState, s = a(o, n);
				if (i.hasEagerState = !0, i.eagerState = s, Sr(s, o)) return ti(e, t, i, 0), Bl === null && ei(), !1;
			} catch {}
			if (n = ni(e, t, i, r), n !== null) return vu(n, e, r), Fs(n, t, r), !0;
		}
		return !1;
	}
	function Ms(e, t, n, r) {
		if (r = {
			lane: 2,
			revertLane: hd(),
			gesture: null,
			action: r,
			hasEagerState: !1,
			eagerState: null,
			next: null
		}, Ns(e)) {
			if (t) throw Error(i(479));
		} else t = ni(e, n, r, 2), t !== null && vu(t, e, 2);
	}
	function Ns(e) {
		var t = e.alternate;
		return e === H || t !== null && t === H;
	}
	function Ps(e, t) {
		ho = mo = !0;
		var n = e.pending;
		n === null ? t.next = t : (t.next = n.next, n.next = t), e.pending = t;
	}
	function Fs(e, t, n) {
		if (n & 4194048) {
			var r = t.lanes;
			r &= e.pendingLanes, n |= r, t.lanes = n, et(e, n);
		}
	}
	var Is = {
		readContext: ta,
		use: Po,
		useCallback: xo,
		useContext: xo,
		useEffect: xo,
		useImperativeHandle: xo,
		useLayoutEffect: xo,
		useInsertionEffect: xo,
		useMemo: xo,
		useReducer: xo,
		useRef: xo,
		useState: xo,
		useDebugValue: xo,
		useDeferredValue: xo,
		useTransition: xo,
		useSyncExternalStore: xo,
		useId: xo,
		useHostTransitionStatus: xo,
		useFormState: xo,
		useActionState: xo,
		useOptimistic: xo,
		useMemoCache: xo,
		useCacheRefresh: xo
	};
	Is.useEffectEvent = xo;
	var Ls = {
		readContext: ta,
		use: Po,
		useCallback: function(e, t) {
			return Ao().memoizedState = [e, t === void 0 ? null : t], e;
		},
		useContext: ta,
		useEffect: ss,
		useImperativeHandle: function(e, t, n) {
			n = n == null ? null : n.concat([e]), as(4194308, 4, ps.bind(null, t, e), n);
		},
		useLayoutEffect: function(e, t) {
			return as(4194308, 4, e, t);
		},
		useInsertionEffect: function(e, t) {
			as(4, 2, e, t);
		},
		useMemo: function(e, t) {
			var n = Ao();
			t = t === void 0 ? null : t;
			var r = e();
			if (go) {
				Le(!0);
				try {
					e();
				} finally {
					Le(!1);
				}
			}
			return n.memoizedState = [r, t], r;
		},
		useReducer: function(e, t, n) {
			var r = Ao();
			if (n !== void 0) {
				var i = n(t);
				if (go) {
					Le(!0);
					try {
						n(t);
					} finally {
						Le(!1);
					}
				}
			} else i = t;
			return r.memoizedState = r.baseState = i, e = {
				pending: null,
				lanes: 0,
				dispatch: null,
				lastRenderedReducer: e,
				lastRenderedState: i
			}, r.queue = e, e = e.dispatch = ks.bind(null, H, e), [r.memoizedState, e];
		},
		useRef: function(e) {
			var t = Ao();
			return e = { current: e }, t.memoizedState = e;
		},
		useState: function(e) {
			e = Ko(e);
			var t = e.queue, n = As.bind(null, H, t);
			return t.dispatch = n, [e.memoizedState, n];
		},
		useDebugValue: hs,
		useDeferredValue: function(e, t) {
			return vs(Ao(), e, t);
		},
		useTransition: function() {
			var e = Ko(!1);
			return e = bs.bind(null, H, e.queue, !0, !1), Ao().memoizedState = e, [!1, e];
		},
		useSyncExternalStore: function(e, t, n) {
			var r = H, a = Ao();
			if (z) {
				if (n === void 0) throw Error(i(407));
				n = n();
			} else {
				if (n = t(), Bl === null) throw Error(i(349));
				q & 127 || Vo(r, t, n);
			}
			a.memoizedState = n;
			var o = {
				value: n,
				getSnapshot: t
			};
			return a.queue = o, ss(Uo.bind(null, r, o, e), [e]), r.flags |= 2048, rs(9, { destroy: void 0 }, Ho.bind(null, r, o, n, t), null), n;
		},
		useId: function() {
			var e = Ao(), t = Bl.identifierPrefix;
			if (z) {
				var n = Di, r = Ei;
				n = (r & ~(1 << 32 - Re(r) - 1)).toString(32) + n, t = "_" + t + "R_" + n, n = _o++, 0 < n && (t += "H" + n.toString(32)), t += "_";
			} else n = bo++, t = "_" + t + "r_" + n.toString(32) + "_";
			return e.memoizedState = t;
		},
		useHostTransitionStatus: Ts,
		useFormState: $o,
		useActionState: $o,
		useOptimistic: function(e) {
			var t = Ao();
			t.memoizedState = t.baseState = e;
			var n = {
				pending: null,
				lanes: 0,
				dispatch: null,
				lastRenderedReducer: null,
				lastRenderedState: null
			};
			return t.queue = n, t = Ms.bind(null, H, !0, n), n.dispatch = t, [e, t];
		},
		useMemoCache: Fo,
		useCacheRefresh: function() {
			return Ao().memoizedState = Os.bind(null, H);
		},
		useEffectEvent: function(e) {
			var t = Ao(), n = { impl: e };
			return t.memoizedState = n, function() {
				if (zl & 2) throw Error(i(440));
				return n.impl.apply(void 0, arguments);
			};
		}
	}, Rs = {
		readContext: ta,
		use: Po,
		useCallback: gs,
		useContext: ta,
		useEffect: cs,
		useImperativeHandle: ms,
		useInsertionEffect: ds,
		useLayoutEffect: fs,
		useMemo: _s,
		useReducer: Lo,
		useRef: is,
		useState: function() {
			return Lo(Io);
		},
		useDebugValue: hs,
		useDeferredValue: function(e, t) {
			return ys(jo(), fo.memoizedState, e, t);
		},
		useTransition: function() {
			var e = Lo(Io)[0], t = jo().memoizedState;
			return [typeof e == "boolean" ? e : No(e), t];
		},
		useSyncExternalStore: Bo,
		useId: Es,
		useHostTransitionStatus: Ts,
		useFormState: es,
		useActionState: es,
		useOptimistic: function(e, t) {
			return qo(jo(), fo, e, t);
		},
		useMemoCache: Fo,
		useCacheRefresh: Ds
	};
	Rs.useEffectEvent = us;
	var zs = {
		readContext: ta,
		use: Po,
		useCallback: gs,
		useContext: ta,
		useEffect: cs,
		useImperativeHandle: ms,
		useInsertionEffect: ds,
		useLayoutEffect: fs,
		useMemo: _s,
		useReducer: zo,
		useRef: is,
		useState: function() {
			return zo(Io);
		},
		useDebugValue: hs,
		useDeferredValue: function(e, t) {
			var n = jo();
			return fo === null ? vs(n, e, t) : ys(n, fo.memoizedState, e, t);
		},
		useTransition: function() {
			var e = zo(Io)[0], t = jo().memoizedState;
			return [typeof e == "boolean" ? e : No(e), t];
		},
		useSyncExternalStore: Bo,
		useId: Es,
		useHostTransitionStatus: Ts,
		useFormState: ns,
		useActionState: ns,
		useOptimistic: function(e, t) {
			var n = jo();
			return fo === null ? (n.baseState = e, [e, n.queue.dispatch]) : qo(n, fo, e, t);
		},
		useMemoCache: Fo,
		useCacheRefresh: Ds
	};
	zs.useEffectEvent = us;
	function Bs(e, t, n, r) {
		t = e.memoizedState, n = n(r, t), n = n == null ? t : f({}, t, n), e.memoizedState = n, e.lanes === 0 && (e.updateQueue.baseState = n);
	}
	var Vs = {
		enqueueSetState: function(e, t, n) {
			e = e._reactInternals;
			var r = gu(), i = Va(r);
			i.payload = t, n != null && (i.callback = n), t = Ha(e, i, r), t !== null && (vu(t, e, r), Ua(t, e, r));
		},
		enqueueReplaceState: function(e, t, n) {
			e = e._reactInternals;
			var r = gu(), i = Va(r);
			i.tag = 1, i.payload = t, n != null && (i.callback = n), t = Ha(e, i, r), t !== null && (vu(t, e, r), Ua(t, e, r));
		},
		enqueueForceUpdate: function(e, t) {
			e = e._reactInternals;
			var n = gu(), r = Va(n);
			r.tag = 2, t != null && (r.callback = t), t = Ha(e, r, n), t !== null && (vu(t, e, n), Ua(t, e, n));
		}
	};
	function Hs(e, t, n, r, i, a, o) {
		return e = e.stateNode, typeof e.shouldComponentUpdate == "function" ? e.shouldComponentUpdate(r, a, o) : t.prototype && t.prototype.isPureReactComponent ? !Cr(n, r) || !Cr(i, a) : !0;
	}
	function Us(e, t, n, r) {
		e = t.state, typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r), typeof t.UNSAFE_componentWillReceiveProps == "function" && t.UNSAFE_componentWillReceiveProps(n, r), t.state !== e && Vs.enqueueReplaceState(t, t.state, null);
	}
	function Ws(e, t) {
		var n = t;
		if ("ref" in t) for (var r in n = {}, t) r !== "ref" && (n[r] = t[r]);
		if (e = e.defaultProps) for (var i in n === t && (n = f({}, n)), e) n[i] === void 0 && (n[i] = e[i]);
		return n;
	}
	function Gs(e) {
		Xr(e);
	}
	function Ks(e) {
		console.error(e);
	}
	function qs(e) {
		Xr(e);
	}
	function Js(e, t) {
		try {
			var n = e.onUncaughtError;
			n(t.value, { componentStack: t.stack });
		} catch (e) {
			setTimeout(function() {
				throw e;
			});
		}
	}
	function Ys(e, t, n) {
		try {
			var r = e.onCaughtError;
			r(n.value, {
				componentStack: n.stack,
				errorBoundary: t.tag === 1 ? t.stateNode : null
			});
		} catch (e) {
			setTimeout(function() {
				throw e;
			});
		}
	}
	function Xs(e, t, n) {
		return n = Va(n), n.tag = 3, n.payload = { element: null }, n.callback = function() {
			Js(e, t);
		}, n;
	}
	function Zs(e) {
		return e = Va(e), e.tag = 3, e;
	}
	function Qs(e, t, n, r) {
		var i = n.type.getDerivedStateFromError;
		if (typeof i == "function") {
			var a = r.value;
			e.payload = function() {
				return i(a);
			}, e.callback = function() {
				Ys(t, n, r);
			};
		}
		var o = n.stateNode;
		o !== null && typeof o.componentDidCatch == "function" && (e.callback = function() {
			Ys(t, n, r), typeof i != "function" && (ou === null ? ou = /* @__PURE__ */ new Set([this]) : ou.add(this));
			var e = r.stack;
			this.componentDidCatch(r.value, { componentStack: e === null ? "" : e });
		});
	}
	function $s(e, t, n, r, a) {
		if (n.flags |= 32768, typeof r == "object" && r && typeof r.then == "function") {
			if (t = n.alternate, t !== null && Qi(t, n, a, !0), n = to.current, n !== null) {
				switch (n.tag) {
					case 31:
					case 13: return no === null ? Au() : n.alternate === null && ql === 0 && (ql = 3), n.flags &= -257, n.flags |= 65536, n.lanes = a, r === Ca ? n.flags |= 16384 : (t = n.updateQueue, t === null ? n.updateQueue = /* @__PURE__ */ new Set([r]) : t.add(r), Yu(e, r, a)), !1;
					case 22: return n.flags |= 65536, r === Ca ? n.flags |= 16384 : (t = n.updateQueue, t === null ? (t = {
						transitions: null,
						markerInstances: null,
						retryQueue: /* @__PURE__ */ new Set([r])
					}, n.updateQueue = t) : (n = t.retryQueue, n === null ? t.retryQueue = /* @__PURE__ */ new Set([r]) : n.add(r)), Yu(e, r, a)), !1;
				}
				throw Error(i(435, n.tag));
			}
			return Yu(e, r, a), Au(), !1;
		}
		if (z) return t = to.current, t === null ? (r !== Li && (t = Error(i(423), { cause: r }), Wi(vi(t, n))), e = e.current.alternate, e.flags |= 65536, a &= -a, e.lanes |= a, r = vi(r, n), a = Xs(e.stateNode, r, a), Wa(e, a), ql !== 4 && (ql = 2)) : (!(t.flags & 65536) && (t.flags |= 256), t.flags |= 65536, t.lanes = a, r !== Li && (e = Error(i(422), { cause: r }), Wi(vi(e, n)))), !1;
		var o = Error(i(520), { cause: r });
		if (o = vi(o, n), $l === null ? $l = [o] : $l.push(o), ql !== 4 && (ql = 2), t === null) return !0;
		r = vi(r, n), n = t;
		do {
			switch (n.tag) {
				case 3: return n.flags |= 65536, e = a & -a, n.lanes |= e, e = Xs(n.stateNode, r, e), Wa(n, e), !1;
				case 1: if (t = n.type, o = n.stateNode, !(n.flags & 128) && (typeof t.getDerivedStateFromError == "function" || o !== null && typeof o.componentDidCatch == "function" && (ou === null || !ou.has(o)))) return n.flags |= 65536, a &= -a, n.lanes |= a, a = Zs(a), Qs(a, e, n, r), Wa(n, a), !1;
			}
			n = n.return;
		} while (n !== null);
		return !1;
	}
	var ec = Error(i(461)), tc = !1;
	function nc(e, t, n, r) {
		t.child = e === null ? La(t, null, n, r) : Ia(t, e.child, n, r);
	}
	function rc(e, t, n, r, i) {
		n = n.render;
		var a = t.ref;
		if ("ref" in r) {
			var o = {};
			for (var s in r) s !== "ref" && (o[s] = r[s]);
		} else o = r;
		return ea(t), r = Co(e, t, n, o, a, i), s = Do(), e !== null && !tc ? (Oo(e, t, i), Dc(e, t, i)) : (z && s && Ai(t), t.flags |= 1, nc(e, t, r, i), t.child);
	}
	function ic(e, t, n, r, i) {
		if (e === null) {
			var a = n.type;
			return typeof a == "function" && !li(a) && a.defaultProps === void 0 && n.compare === null ? (t.tag = 15, t.type = a, ac(e, t, a, r, i)) : (e = fi(n.type, null, r, t, t.mode, i), e.ref = t.ref, e.return = t, t.child = e);
		}
		if (a = e.child, !Oc(e, i)) {
			var o = a.memoizedProps;
			if (n = n.compare, n = n === null ? Cr : n, n(o, r) && e.ref === t.ref) return Dc(e, t, i);
		}
		return t.flags |= 1, e = ui(a, r), e.ref = t.ref, e.return = t, t.child = e;
	}
	function ac(e, t, n, r, i) {
		if (e !== null) {
			var a = e.memoizedProps;
			if (Cr(a, r) && e.ref === t.ref) if (tc = !1, t.pendingProps = r = a, Oc(e, i)) e.flags & 131072 && (tc = !0);
			else return t.lanes = e.lanes, Dc(e, t, i);
		}
		return pc(e, t, n, r, i);
	}
	function oc(e, t, n, r) {
		var i = r.children, a = e === null ? null : e.memoizedState;
		if (e === null && t.stateNode === null && (t.stateNode = {
			_visibility: 1,
			_pendingMarkers: null,
			_retryCache: null,
			_transitions: null
		}), r.mode === "hidden") {
			if (t.flags & 128) {
				if (a = a === null ? n : a.baseLanes | n, e !== null) {
					for (r = t.child = e.child, i = 0; r !== null;) i = i | r.lanes | r.childLanes, r = r.sibling;
					r = i & ~a;
				} else r = 0, t.child = null;
				return cc(e, t, a, n, r);
			}
			if (n & 536870912) t.memoizedState = {
				baseLanes: 0,
				cachePool: null
			}, e !== null && va(t, a === null ? null : a.cachePool), a === null ? $a() : Qa(t, a), ao(t);
			else return r = t.lanes = 536870912, cc(e, t, a === null ? n : a.baseLanes | n, n, r);
		} else a === null ? (e !== null && va(t, null), $a(), oo(t)) : (va(t, a.cachePool), Qa(t, a), oo(t), t.memoizedState = null);
		return nc(e, t, i, n), t.child;
	}
	function sc(e, t) {
		return e !== null && e.tag === 22 || t.stateNode !== null || (t.stateNode = {
			_visibility: 1,
			_pendingMarkers: null,
			_retryCache: null,
			_transitions: null
		}), t.sibling;
	}
	function cc(e, t, n, r, i) {
		var a = _a();
		return a = a === null ? null : {
			parent: sa._currentValue,
			pool: a
		}, t.memoizedState = {
			baseLanes: n,
			cachePool: a
		}, e !== null && va(t, null), $a(), ao(t), e !== null && Qi(e, t, r, !0), t.childLanes = i, null;
	}
	function lc(e, t) {
		return t = Sc({
			mode: t.mode,
			children: t.children
		}, e.mode), t.ref = e.ref, e.child = t, t.return = e, t;
	}
	function uc(e, t, n) {
		return Ia(t, e.child, null, n), e = lc(t, t.pendingProps), e.flags |= 2, so(t), t.memoizedState = null, e;
	}
	function dc(e, t, n) {
		var r = t.pendingProps, a = (t.flags & 128) != 0;
		if (t.flags &= -129, e === null) {
			if (z) {
				if (r.mode === "hidden") return e = lc(t, r), t.lanes = 536870912, sc(null, e);
				if (io(t), (e = Pi) ? (e = cf(e, Ii), e = e !== null && e.data === "&" ? e : null, e !== null && (t.memoizedState = {
					dehydrated: e,
					treeContext: Ti === null ? null : {
						id: Ei,
						overflow: Di
					},
					retryLane: 536870912,
					hydrationErrors: null
				}, n = hi(e), n.return = t, t.child = n, Ni = t, Pi = null)) : e = null, e === null) throw Ri(t);
				return t.lanes = 536870912, null;
			}
			return lc(t, r);
		}
		var o = e.memoizedState;
		if (o !== null) {
			var s = o.dehydrated;
			if (io(t), a) if (t.flags & 256) t.flags &= -257, t = uc(e, t, n);
			else if (t.memoizedState !== null) t.child = e.child, t.flags |= 128, t = null;
			else throw Error(i(558));
			else if (tc || Qi(e, t, n, !1), a = (n & e.childLanes) !== 0, tc || a) {
				if (r = Bl, r !== null && (s = tt(r, n), s !== 0 && s !== o.retryLane)) throw o.retryLane = s, ri(e, s), vu(r, e, s), ec;
				Au(), t = uc(e, t, n);
			} else e = o.treeContext, Pi = ff(s.nextSibling), Ni = t, z = !0, Fi = null, Ii = !1, e !== null && Mi(t, e), t = lc(t, r), t.flags |= 4096;
			return t;
		}
		return e = ui(e.child, {
			mode: r.mode,
			children: r.children
		}), e.ref = t.ref, t.child = e, e.return = t, e;
	}
	function fc(e, t) {
		var n = t.ref;
		if (n === null) e !== null && e.ref !== null && (t.flags |= 4194816);
		else {
			if (typeof n != "function" && typeof n != "object") throw Error(i(284));
			(e === null || e.ref !== n) && (t.flags |= 4194816);
		}
	}
	function pc(e, t, n, r, i) {
		return ea(t), n = Co(e, t, n, r, void 0, i), r = Do(), e !== null && !tc ? (Oo(e, t, i), Dc(e, t, i)) : (z && r && Ai(t), t.flags |= 1, nc(e, t, n, i), t.child);
	}
	function mc(e, t, n, r, i, a) {
		return ea(t), t.updateQueue = null, n = To(t, r, n, i), wo(e), r = Do(), e !== null && !tc ? (Oo(e, t, a), Dc(e, t, a)) : (z && r && Ai(t), t.flags |= 1, nc(e, t, n, a), t.child);
	}
	function hc(e, t, n, r, i) {
		if (ea(t), t.stateNode === null) {
			var a = oi, o = n.contextType;
			typeof o == "object" && o && (a = ta(o)), a = new n(r, a), t.memoizedState = a.state !== null && a.state !== void 0 ? a.state : null, a.updater = Vs, t.stateNode = a, a._reactInternals = t, a = t.stateNode, a.props = r, a.state = t.memoizedState, a.refs = {}, za(t), o = n.contextType, a.context = typeof o == "object" && o ? ta(o) : oi, a.state = t.memoizedState, o = n.getDerivedStateFromProps, typeof o == "function" && (Bs(t, n, o, r), a.state = t.memoizedState), typeof n.getDerivedStateFromProps == "function" || typeof a.getSnapshotBeforeUpdate == "function" || typeof a.UNSAFE_componentWillMount != "function" && typeof a.componentWillMount != "function" || (o = a.state, typeof a.componentWillMount == "function" && a.componentWillMount(), typeof a.UNSAFE_componentWillMount == "function" && a.UNSAFE_componentWillMount(), o !== a.state && Vs.enqueueReplaceState(a, a.state, null), qa(t, r, a, i), Ka(), a.state = t.memoizedState), typeof a.componentDidMount == "function" && (t.flags |= 4194308), r = !0;
		} else if (e === null) {
			a = t.stateNode;
			var s = t.memoizedProps, c = Ws(n, s);
			a.props = c;
			var l = a.context, u = n.contextType;
			o = oi, typeof u == "object" && u && (o = ta(u));
			var d = n.getDerivedStateFromProps;
			u = typeof d == "function" || typeof a.getSnapshotBeforeUpdate == "function", s = t.pendingProps !== s, u || typeof a.UNSAFE_componentWillReceiveProps != "function" && typeof a.componentWillReceiveProps != "function" || (s || l !== o) && Us(t, a, r, o), Ra = !1;
			var f = t.memoizedState;
			a.state = f, qa(t, r, a, i), Ka(), l = t.memoizedState, s || f !== l || Ra ? (typeof d == "function" && (Bs(t, n, d, r), l = t.memoizedState), (c = Ra || Hs(t, n, c, r, f, l, o)) ? (u || typeof a.UNSAFE_componentWillMount != "function" && typeof a.componentWillMount != "function" || (typeof a.componentWillMount == "function" && a.componentWillMount(), typeof a.UNSAFE_componentWillMount == "function" && a.UNSAFE_componentWillMount()), typeof a.componentDidMount == "function" && (t.flags |= 4194308)) : (typeof a.componentDidMount == "function" && (t.flags |= 4194308), t.memoizedProps = r, t.memoizedState = l), a.props = r, a.state = l, a.context = o, r = c) : (typeof a.componentDidMount == "function" && (t.flags |= 4194308), r = !1);
		} else {
			a = t.stateNode, Ba(e, t), o = t.memoizedProps, u = Ws(n, o), a.props = u, d = t.pendingProps, f = a.context, l = n.contextType, c = oi, typeof l == "object" && l && (c = ta(l)), s = n.getDerivedStateFromProps, (l = typeof s == "function" || typeof a.getSnapshotBeforeUpdate == "function") || typeof a.UNSAFE_componentWillReceiveProps != "function" && typeof a.componentWillReceiveProps != "function" || (o !== d || f !== c) && Us(t, a, r, c), Ra = !1, f = t.memoizedState, a.state = f, qa(t, r, a, i), Ka();
			var p = t.memoizedState;
			o !== d || f !== p || Ra || e !== null && e.dependencies !== null && $i(e.dependencies) ? (typeof s == "function" && (Bs(t, n, s, r), p = t.memoizedState), (u = Ra || Hs(t, n, u, r, f, p, c) || e !== null && e.dependencies !== null && $i(e.dependencies)) ? (l || typeof a.UNSAFE_componentWillUpdate != "function" && typeof a.componentWillUpdate != "function" || (typeof a.componentWillUpdate == "function" && a.componentWillUpdate(r, p, c), typeof a.UNSAFE_componentWillUpdate == "function" && a.UNSAFE_componentWillUpdate(r, p, c)), typeof a.componentDidUpdate == "function" && (t.flags |= 4), typeof a.getSnapshotBeforeUpdate == "function" && (t.flags |= 1024)) : (typeof a.componentDidUpdate != "function" || o === e.memoizedProps && f === e.memoizedState || (t.flags |= 4), typeof a.getSnapshotBeforeUpdate != "function" || o === e.memoizedProps && f === e.memoizedState || (t.flags |= 1024), t.memoizedProps = r, t.memoizedState = p), a.props = r, a.state = p, a.context = c, r = u) : (typeof a.componentDidUpdate != "function" || o === e.memoizedProps && f === e.memoizedState || (t.flags |= 4), typeof a.getSnapshotBeforeUpdate != "function" || o === e.memoizedProps && f === e.memoizedState || (t.flags |= 1024), r = !1);
		}
		return a = r, fc(e, t), r = (t.flags & 128) != 0, a || r ? (a = t.stateNode, n = r && typeof n.getDerivedStateFromError != "function" ? null : a.render(), t.flags |= 1, e !== null && r ? (t.child = Ia(t, e.child, null, i), t.child = Ia(t, null, n, i)) : nc(e, t, n, i), t.memoizedState = a.state, e = t.child) : e = Dc(e, t, i), e;
	}
	function gc(e, t, n, r) {
		return Hi(), t.flags |= 256, nc(e, t, n, r), t.child;
	}
	var _c = {
		dehydrated: null,
		treeContext: null,
		retryLane: 0,
		hydrationErrors: null
	};
	function vc(e) {
		return {
			baseLanes: e,
			cachePool: ya()
		};
	}
	function yc(e, t, n) {
		return e = e === null ? 0 : e.childLanes & ~n, t && (e |= Zl), e;
	}
	function bc(e, t, n) {
		var r = t.pendingProps, a = !1, o = (t.flags & 128) != 0, s;
		if ((s = o) || (s = e !== null && e.memoizedState === null ? !1 : (co.current & 2) != 0), s && (a = !0, t.flags &= -129), s = (t.flags & 32) != 0, t.flags &= -33, e === null) {
			if (z) {
				if (a ? ro(t) : oo(t), (e = Pi) ? (e = cf(e, Ii), e = e !== null && e.data !== "&" ? e : null, e !== null && (t.memoizedState = {
					dehydrated: e,
					treeContext: Ti === null ? null : {
						id: Ei,
						overflow: Di
					},
					retryLane: 536870912,
					hydrationErrors: null
				}, n = hi(e), n.return = t, t.child = n, Ni = t, Pi = null)) : e = null, e === null) throw Ri(t);
				return uf(e) ? t.lanes = 32 : t.lanes = 536870912, null;
			}
			var c = r.children;
			return r = r.fallback, a ? (oo(t), a = t.mode, c = Sc({
				mode: "hidden",
				children: c
			}, a), r = pi(r, a, n, null), c.return = t, r.return = t, c.sibling = r, t.child = c, r = t.child, r.memoizedState = vc(n), r.childLanes = yc(e, s, n), t.memoizedState = _c, sc(null, r)) : (ro(t), xc(t, c));
		}
		var l = e.memoizedState;
		if (l !== null && (c = l.dehydrated, c !== null)) {
			if (o) t.flags & 256 ? (ro(t), t.flags &= -257, t = Cc(e, t, n)) : t.memoizedState === null ? (oo(t), c = r.fallback, a = t.mode, r = Sc({
				mode: "visible",
				children: r.children
			}, a), c = pi(c, a, n, null), c.flags |= 2, r.return = t, c.return = t, r.sibling = c, t.child = r, Ia(t, e.child, null, n), r = t.child, r.memoizedState = vc(n), r.childLanes = yc(e, s, n), t.memoizedState = _c, t = sc(null, r)) : (oo(t), t.child = e.child, t.flags |= 128, t = null);
			else if (ro(t), uf(c)) {
				if (s = c.nextSibling && c.nextSibling.dataset, s) var u = s.dgst;
				s = u, r = Error(i(419)), r.stack = "", r.digest = s, Wi({
					value: r,
					source: null,
					stack: null
				}), t = Cc(e, t, n);
			} else if (tc || Qi(e, t, n, !1), s = (n & e.childLanes) !== 0, tc || s) {
				if (s = Bl, s !== null && (r = tt(s, n), r !== 0 && r !== l.retryLane)) throw l.retryLane = r, ri(e, r), vu(s, e, r), ec;
				lf(c) || Au(), t = Cc(e, t, n);
			} else lf(c) ? (t.flags |= 192, t.child = e.child, t = null) : (e = l.treeContext, Pi = ff(c.nextSibling), Ni = t, z = !0, Fi = null, Ii = !1, e !== null && Mi(t, e), t = xc(t, r.children), t.flags |= 4096);
			return t;
		}
		return a ? (oo(t), c = r.fallback, a = t.mode, l = e.child, u = l.sibling, r = ui(l, {
			mode: "hidden",
			children: r.children
		}), r.subtreeFlags = l.subtreeFlags & 65011712, u === null ? (c = pi(c, a, n, null), c.flags |= 2) : c = ui(u, c), c.return = t, r.return = t, r.sibling = c, t.child = r, sc(null, r), r = t.child, c = e.child.memoizedState, c === null ? c = vc(n) : (a = c.cachePool, a === null ? a = ya() : (l = sa._currentValue, a = a.parent === l ? a : {
			parent: l,
			pool: l
		}), c = {
			baseLanes: c.baseLanes | n,
			cachePool: a
		}), r.memoizedState = c, r.childLanes = yc(e, s, n), t.memoizedState = _c, sc(e.child, r)) : (ro(t), n = e.child, e = n.sibling, n = ui(n, {
			mode: "visible",
			children: r.children
		}), n.return = t, n.sibling = null, e !== null && (s = t.deletions, s === null ? (t.deletions = [e], t.flags |= 16) : s.push(e)), t.child = n, t.memoizedState = null, n);
	}
	function xc(e, t) {
		return t = Sc({
			mode: "visible",
			children: t
		}, e.mode), t.return = e, e.child = t;
	}
	function Sc(e, t) {
		return e = ci(22, e, null, t), e.lanes = 0, e;
	}
	function Cc(e, t, n) {
		return Ia(t, e.child, null, n), e = xc(t, t.pendingProps.children), e.flags |= 2, t.memoizedState = null, e;
	}
	function wc(e, t, n) {
		e.lanes |= t;
		var r = e.alternate;
		r !== null && (r.lanes |= t), Xi(e.return, t, n);
	}
	function Tc(e, t, n, r, i, a) {
		var o = e.memoizedState;
		o === null ? e.memoizedState = {
			isBackwards: t,
			rendering: null,
			renderingStartTime: 0,
			last: r,
			tail: n,
			tailMode: i,
			treeForkCount: a
		} : (o.isBackwards = t, o.rendering = null, o.renderingStartTime = 0, o.last = r, o.tail = n, o.tailMode = i, o.treeForkCount = a);
	}
	function Ec(e, t, n) {
		var r = t.pendingProps, i = r.revealOrder, a = r.tail;
		r = r.children;
		var o = co.current, s = (o & 2) != 0;
		if (s ? (o = o & 1 | 2, t.flags |= 128) : o &= 1, F(co, o), nc(e, t, r, n), r = z ? Si : 0, !s && e !== null && e.flags & 128) a: for (e = t.child; e !== null;) {
			if (e.tag === 13) e.memoizedState !== null && wc(e, n, t);
			else if (e.tag === 19) wc(e, n, t);
			else if (e.child !== null) {
				e.child.return = e, e = e.child;
				continue;
			}
			if (e === t) break a;
			for (; e.sibling === null;) {
				if (e.return === null || e.return === t) break a;
				e = e.return;
			}
			e.sibling.return = e.return, e = e.sibling;
		}
		switch (i) {
			case "forwards":
				for (n = t.child, i = null; n !== null;) e = n.alternate, e !== null && lo(e) === null && (i = n), n = n.sibling;
				n = i, n === null ? (i = t.child, t.child = null) : (i = n.sibling, n.sibling = null), Tc(t, !1, i, n, a, r);
				break;
			case "backwards":
			case "unstable_legacy-backwards":
				for (n = null, i = t.child, t.child = null; i !== null;) {
					if (e = i.alternate, e !== null && lo(e) === null) {
						t.child = i;
						break;
					}
					e = i.sibling, i.sibling = n, n = i, i = e;
				}
				Tc(t, !0, n, null, a, r);
				break;
			case "together":
				Tc(t, !1, null, null, void 0, r);
				break;
			default: t.memoizedState = null;
		}
		return t.child;
	}
	function Dc(e, t, n) {
		if (e !== null && (t.dependencies = e.dependencies), Jl |= t.lanes, (n & t.childLanes) === 0) if (e !== null) {
			if (Qi(e, t, n, !1), (n & t.childLanes) === 0) return null;
		} else return null;
		if (e !== null && t.child !== e.child) throw Error(i(153));
		if (t.child !== null) {
			for (e = t.child, n = ui(e, e.pendingProps), t.child = n, n.return = t; e.sibling !== null;) e = e.sibling, n = n.sibling = ui(e, e.pendingProps), n.return = t;
			n.sibling = null;
		}
		return t.child;
	}
	function Oc(e, t) {
		return (e.lanes & t) === 0 ? (e = e.dependencies, !!(e !== null && $i(e))) : !0;
	}
	function kc(e, t, n) {
		switch (t.tag) {
			case 3:
				ue(t, t.stateNode.containerInfo), Ji(t, sa, e.memoizedState.cache), Hi();
				break;
			case 27:
			case 5:
				me(t);
				break;
			case 4:
				ue(t, t.stateNode.containerInfo);
				break;
			case 10:
				Ji(t, t.type, t.memoizedProps.value);
				break;
			case 31:
				if (t.memoizedState !== null) return t.flags |= 128, io(t), null;
				break;
			case 13:
				var r = t.memoizedState;
				if (r !== null) return r.dehydrated === null ? (n & t.child.childLanes) === 0 ? (ro(t), e = Dc(e, t, n), e === null ? null : e.sibling) : bc(e, t, n) : (ro(t), t.flags |= 128, null);
				ro(t);
				break;
			case 19:
				var i = (e.flags & 128) != 0;
				if (r = (n & t.childLanes) !== 0, r ||= (Qi(e, t, n, !1), (n & t.childLanes) !== 0), i) {
					if (r) return Ec(e, t, n);
					t.flags |= 128;
				}
				if (i = t.memoizedState, i !== null && (i.rendering = null, i.tail = null, i.lastEffect = null), F(co, co.current), r) break;
				return null;
			case 22: return t.lanes = 0, oc(e, t, n, t.pendingProps);
			case 24: Ji(t, sa, e.memoizedState.cache);
		}
		return Dc(e, t, n);
	}
	function Ac(e, t, n) {
		if (e !== null) if (e.memoizedProps !== t.pendingProps) tc = !0;
		else {
			if (!Oc(e, n) && !(t.flags & 128)) return tc = !1, kc(e, t, n);
			tc = !!(e.flags & 131072);
		}
		else tc = !1, z && t.flags & 1048576 && ki(t, Si, t.index);
		switch (t.lanes = 0, t.tag) {
			case 16:
				a: {
					var r = t.pendingProps;
					if (e = Ea(t.elementType), t.type = e, typeof e == "function") li(e) ? (r = Ws(e, r), t.tag = 1, t = hc(null, t, e, r, n)) : (t.tag = 0, t = pc(null, t, e, r, n));
					else {
						if (e != null) {
							var a = e.$$typeof;
							if (a === x) {
								t.tag = 11, t = rc(null, t, e, r, n);
								break a;
							} else if (a === w) {
								t.tag = 14, t = ic(null, t, e, r, n);
								break a;
							}
						}
						throw t = A(e) || e, Error(i(306, t, ""));
					}
				}
				return t;
			case 0: return pc(e, t, t.type, t.pendingProps, n);
			case 1: return r = t.type, a = Ws(r, t.pendingProps), hc(e, t, r, a, n);
			case 3:
				a: {
					if (ue(t, t.stateNode.containerInfo), e === null) throw Error(i(387));
					r = t.pendingProps;
					var o = t.memoizedState;
					a = o.element, Ba(e, t), qa(t, r, null, n);
					var s = t.memoizedState;
					if (r = s.cache, Ji(t, sa, r), r !== o.cache && Zi(t, [sa], n, !0), Ka(), r = s.element, o.isDehydrated) if (o = {
						element: r,
						isDehydrated: !1,
						cache: s.cache
					}, t.updateQueue.baseState = o, t.memoizedState = o, t.flags & 256) {
						t = gc(e, t, r, n);
						break a;
					} else if (r !== a) {
						a = vi(Error(i(424)), t), Wi(a), t = gc(e, t, r, n);
						break a;
					} else {
						switch (e = t.stateNode.containerInfo, e.nodeType) {
							case 9:
								e = e.body;
								break;
							default: e = e.nodeName === "HTML" ? e.ownerDocument.body : e;
						}
						for (Pi = ff(e.firstChild), Ni = t, z = !0, Fi = null, Ii = !0, n = La(t, null, r, n), t.child = n; n;) n.flags = n.flags & -3 | 4096, n = n.sibling;
					}
					else {
						if (Hi(), r === a) {
							t = Dc(e, t, n);
							break a;
						}
						nc(e, t, r, n);
					}
					t = t.child;
				}
				return t;
			case 26: return fc(e, t), e === null ? (n = Nf(t.type, null, t.pendingProps, null)) ? t.memoizedState = n : z || (n = t.type, e = t.pendingProps, r = Wd(se.current).createElement(n), r[ot] = t, r[st] = e, Rd(r, n, e), yt(r), t.stateNode = r) : t.memoizedState = Nf(t.type, e.memoizedProps, t.pendingProps, e.memoizedState), null;
			case 27: return me(t), e === null && z && (r = t.stateNode = gf(t.type, t.pendingProps, se.current), Ni = t, Ii = !0, a = Pi, tf(t.type) ? (pf = a, Pi = ff(r.firstChild)) : Pi = a), nc(e, t, t.pendingProps.children, n), fc(e, t), e === null && (t.flags |= 4194304), t.child;
			case 5: return e === null && z && ((a = r = Pi) && (r = of(r, t.type, t.pendingProps, Ii), r === null ? a = !1 : (t.stateNode = r, Ni = t, Pi = ff(r.firstChild), Ii = !1, a = !0)), a || Ri(t)), me(t), a = t.type, o = t.pendingProps, s = e === null ? null : e.memoizedProps, r = o.children, qd(a, o) ? r = null : s !== null && qd(a, s) && (t.flags |= 32), t.memoizedState !== null && (a = Co(e, t, Eo, null, null, n), np._currentValue = a), fc(e, t), nc(e, t, r, n), t.child;
			case 6: return e === null && z && ((e = n = Pi) && (n = sf(n, t.pendingProps, Ii), n === null ? e = !1 : (t.stateNode = n, Ni = t, Pi = null, e = !0)), e || Ri(t)), null;
			case 13: return bc(e, t, n);
			case 4: return ue(t, t.stateNode.containerInfo), r = t.pendingProps, e === null ? t.child = Ia(t, null, r, n) : nc(e, t, r, n), t.child;
			case 11: return rc(e, t, t.type, t.pendingProps, n);
			case 7: return nc(e, t, t.pendingProps, n), t.child;
			case 8: return nc(e, t, t.pendingProps.children, n), t.child;
			case 12: return nc(e, t, t.pendingProps.children, n), t.child;
			case 10: return r = t.pendingProps, Ji(t, t.type, r.value), nc(e, t, r.children, n), t.child;
			case 9: return a = t.type._context, r = t.pendingProps.children, ea(t), a = ta(a), r = r(a), t.flags |= 1, nc(e, t, r, n), t.child;
			case 14: return ic(e, t, t.type, t.pendingProps, n);
			case 15: return ac(e, t, t.type, t.pendingProps, n);
			case 19: return Ec(e, t, n);
			case 31: return dc(e, t, n);
			case 22: return oc(e, t, n, t.pendingProps);
			case 24: return ea(t), r = ta(sa), e === null ? (a = _a(), a === null && (a = Bl, o = ca(), a.pooledCache = o, o.refCount++, o !== null && (a.pooledCacheLanes |= n), a = o), t.memoizedState = {
				parent: r,
				cache: a
			}, za(t), Ji(t, sa, a)) : ((e.lanes & n) !== 0 && (Ba(e, t), qa(t, null, null, n), Ka()), a = e.memoizedState, o = t.memoizedState, a.parent === r ? (r = o.cache, Ji(t, sa, r), r !== a.cache && Zi(t, [sa], n, !0)) : (a = {
				parent: r,
				cache: r
			}, t.memoizedState = a, t.lanes === 0 && (t.memoizedState = t.updateQueue.baseState = a), Ji(t, sa, r))), nc(e, t, t.pendingProps.children, n), t.child;
			case 29: throw t.pendingProps;
		}
		throw Error(i(156, t.tag));
	}
	function jc(e) {
		e.flags |= 4;
	}
	function Mc(e, t, n, r, i) {
		if ((t = (e.mode & 32) != 0) && (t = !1), t) {
			if (e.flags |= 16777216, (i & 335544128) === i) if (e.stateNode.complete) e.flags |= 8192;
			else if (Du()) e.flags |= 8192;
			else throw Da = Ca, xa;
		} else e.flags &= -16777217;
	}
	function Nc(e, t) {
		if (t.type !== "stylesheet" || t.state.loading & 4) e.flags &= -16777217;
		else if (e.flags |= 16777216, !Jf(t)) if (Du()) e.flags |= 8192;
		else throw Da = Ca, xa;
	}
	function Pc(e, t) {
		t !== null && (e.flags |= 4), e.flags & 16384 && (t = e.tag === 22 ? 536870912 : Ye(), e.lanes |= t, Ql |= t);
	}
	function Fc(e, t) {
		if (!z) switch (e.tailMode) {
			case "hidden":
				t = e.tail;
				for (var n = null; t !== null;) t.alternate !== null && (n = t), t = t.sibling;
				n === null ? e.tail = null : n.sibling = null;
				break;
			case "collapsed":
				n = e.tail;
				for (var r = null; n !== null;) n.alternate !== null && (r = n), n = n.sibling;
				r === null ? t || e.tail === null ? e.tail = null : e.tail.sibling = null : r.sibling = null;
		}
	}
	function Ic(e) {
		var t = e.alternate !== null && e.alternate.child === e.child, n = 0, r = 0;
		if (t) for (var i = e.child; i !== null;) n |= i.lanes | i.childLanes, r |= i.subtreeFlags & 65011712, r |= i.flags & 65011712, i.return = e, i = i.sibling;
		else for (i = e.child; i !== null;) n |= i.lanes | i.childLanes, r |= i.subtreeFlags, r |= i.flags, i.return = e, i = i.sibling;
		return e.subtreeFlags |= r, e.childLanes = n, t;
	}
	function Lc(e, t, n) {
		var r = t.pendingProps;
		switch (ji(t), t.tag) {
			case 16:
			case 15:
			case 0:
			case 11:
			case 7:
			case 8:
			case 12:
			case 9:
			case 14: return Ic(t), null;
			case 1: return Ic(t), null;
			case 3: return n = t.stateNode, r = null, e !== null && (r = e.memoizedState.cache), t.memoizedState.cache !== r && (t.flags |= 2048), Yi(sa), fe(), n.pendingContext && (n.context = n.pendingContext, n.pendingContext = null), (e === null || e.child === null) && (Vi(t) ? jc(t) : e === null || e.memoizedState.isDehydrated && !(t.flags & 256) || (t.flags |= 1024, Ui())), Ic(t), null;
			case 26:
				var a = t.type, o = t.memoizedState;
				return e === null ? (jc(t), o === null ? (Ic(t), Mc(t, a, null, r, n)) : (Ic(t), Nc(t, o))) : o ? o === e.memoizedState ? (Ic(t), t.flags &= -16777217) : (jc(t), Ic(t), Nc(t, o)) : (e = e.memoizedProps, e !== r && jc(t), Ic(t), Mc(t, a, e, r, n)), null;
			case 27:
				if (he(t), n = se.current, a = t.type, e !== null && t.stateNode != null) e.memoizedProps !== r && jc(t);
				else {
					if (!r) {
						if (t.stateNode === null) throw Error(i(166));
						return Ic(t), null;
					}
					e = ae.current, Vi(t) ? zi(t, e) : (e = gf(a, r, n), t.stateNode = e, jc(t));
				}
				return Ic(t), null;
			case 5:
				if (he(t), a = t.type, e !== null && t.stateNode != null) e.memoizedProps !== r && jc(t);
				else {
					if (!r) {
						if (t.stateNode === null) throw Error(i(166));
						return Ic(t), null;
					}
					if (o = ae.current, Vi(t)) zi(t, o);
					else {
						var s = Wd(se.current);
						switch (o) {
							case 1:
								o = s.createElementNS("http://www.w3.org/2000/svg", a);
								break;
							case 2:
								o = s.createElementNS("http://www.w3.org/1998/Math/MathML", a);
								break;
							default: switch (a) {
								case "svg":
									o = s.createElementNS("http://www.w3.org/2000/svg", a);
									break;
								case "math":
									o = s.createElementNS("http://www.w3.org/1998/Math/MathML", a);
									break;
								case "script":
									o = s.createElement("div"), o.innerHTML = "<script><\/script>", o = o.removeChild(o.firstChild);
									break;
								case "select":
									o = typeof r.is == "string" ? s.createElement("select", { is: r.is }) : s.createElement("select"), r.multiple ? o.multiple = !0 : r.size && (o.size = r.size);
									break;
								default: o = typeof r.is == "string" ? s.createElement(a, { is: r.is }) : s.createElement(a);
							}
						}
						o[ot] = t, o[st] = r;
						a: for (s = t.child; s !== null;) {
							if (s.tag === 5 || s.tag === 6) o.appendChild(s.stateNode);
							else if (s.tag !== 4 && s.tag !== 27 && s.child !== null) {
								s.child.return = s, s = s.child;
								continue;
							}
							if (s === t) break a;
							for (; s.sibling === null;) {
								if (s.return === null || s.return === t) break a;
								s = s.return;
							}
							s.sibling.return = s.return, s = s.sibling;
						}
						t.stateNode = o;
						a: switch (Rd(o, a, r), a) {
							case "button":
							case "input":
							case "select":
							case "textarea":
								r = !!r.autoFocus;
								break a;
							case "img":
								r = !0;
								break a;
							default: r = !1;
						}
						r && jc(t);
					}
				}
				return Ic(t), Mc(t, t.type, e === null ? null : e.memoizedProps, t.pendingProps, n), null;
			case 6:
				if (e && t.stateNode != null) e.memoizedProps !== r && jc(t);
				else {
					if (typeof r != "string" && t.stateNode === null) throw Error(i(166));
					if (e = se.current, Vi(t)) {
						if (e = t.stateNode, n = t.memoizedProps, r = null, a = Ni, a !== null) switch (a.tag) {
							case 27:
							case 5: r = a.memoizedProps;
						}
						e[ot] = t, e = !!(e.nodeValue === n || r !== null && !0 === r.suppressHydrationWarning || Fd(e.nodeValue, n)), e || Ri(t, !0);
					} else e = Wd(e).createTextNode(r), e[ot] = t, t.stateNode = e;
				}
				return Ic(t), null;
			case 31:
				if (n = t.memoizedState, e === null || e.memoizedState !== null) {
					if (r = Vi(t), n !== null) {
						if (e === null) {
							if (!r) throw Error(i(318));
							if (e = t.memoizedState, e = e === null ? null : e.dehydrated, !e) throw Error(i(557));
							e[ot] = t;
						} else Hi(), !(t.flags & 128) && (t.memoizedState = null), t.flags |= 4;
						Ic(t), e = !1;
					} else n = Ui(), e !== null && e.memoizedState !== null && (e.memoizedState.hydrationErrors = n), e = !0;
					if (!e) return t.flags & 256 ? (so(t), t) : (so(t), null);
					if (t.flags & 128) throw Error(i(558));
				}
				return Ic(t), null;
			case 13:
				if (r = t.memoizedState, e === null || e.memoizedState !== null && e.memoizedState.dehydrated !== null) {
					if (a = Vi(t), r !== null && r.dehydrated !== null) {
						if (e === null) {
							if (!a) throw Error(i(318));
							if (a = t.memoizedState, a = a === null ? null : a.dehydrated, !a) throw Error(i(317));
							a[ot] = t;
						} else Hi(), !(t.flags & 128) && (t.memoizedState = null), t.flags |= 4;
						Ic(t), a = !1;
					} else a = Ui(), e !== null && e.memoizedState !== null && (e.memoizedState.hydrationErrors = a), a = !0;
					if (!a) return t.flags & 256 ? (so(t), t) : (so(t), null);
				}
				return so(t), t.flags & 128 ? (t.lanes = n, t) : (n = r !== null, e = e !== null && e.memoizedState !== null, n && (r = t.child, a = null, r.alternate !== null && r.alternate.memoizedState !== null && r.alternate.memoizedState.cachePool !== null && (a = r.alternate.memoizedState.cachePool.pool), o = null, r.memoizedState !== null && r.memoizedState.cachePool !== null && (o = r.memoizedState.cachePool.pool), o !== a && (r.flags |= 2048)), n !== e && n && (t.child.flags |= 8192), Pc(t, t.updateQueue), Ic(t), null);
			case 4: return fe(), e === null && Td(t.stateNode.containerInfo), Ic(t), null;
			case 10: return Yi(t.type), Ic(t), null;
			case 19:
				if (ie(co), r = t.memoizedState, r === null) return Ic(t), null;
				if (a = (t.flags & 128) != 0, o = r.rendering, o === null) if (a) Fc(r, !1);
				else {
					if (ql !== 0 || e !== null && e.flags & 128) for (e = t.child; e !== null;) {
						if (o = lo(e), o !== null) {
							for (t.flags |= 128, Fc(r, !1), e = o.updateQueue, t.updateQueue = e, Pc(t, e), t.subtreeFlags = 0, e = n, n = t.child; n !== null;) di(n, e), n = n.sibling;
							return F(co, co.current & 1 | 2), z && Oi(t, r.treeForkCount), t.child;
						}
						e = e.sibling;
					}
					r.tail !== null && Ee() > iu && (t.flags |= 128, a = !0, Fc(r, !1), t.lanes = 4194304);
				}
				else {
					if (!a) if (e = lo(o), e !== null) {
						if (t.flags |= 128, a = !0, e = e.updateQueue, t.updateQueue = e, Pc(t, e), Fc(r, !0), r.tail === null && r.tailMode === "hidden" && !o.alternate && !z) return Ic(t), null;
					} else 2 * Ee() - r.renderingStartTime > iu && n !== 536870912 && (t.flags |= 128, a = !0, Fc(r, !1), t.lanes = 4194304);
					r.isBackwards ? (o.sibling = t.child, t.child = o) : (e = r.last, e === null ? t.child = o : e.sibling = o, r.last = o);
				}
				return r.tail === null ? (Ic(t), null) : (e = r.tail, r.rendering = e, r.tail = e.sibling, r.renderingStartTime = Ee(), e.sibling = null, n = co.current, F(co, a ? n & 1 | 2 : n & 1), z && Oi(t, r.treeForkCount), e);
			case 22:
			case 23: return so(t), eo(), r = t.memoizedState !== null, e === null ? r && (t.flags |= 8192) : e.memoizedState !== null !== r && (t.flags |= 8192), r ? n & 536870912 && !(t.flags & 128) && (Ic(t), t.subtreeFlags & 6 && (t.flags |= 8192)) : Ic(t), n = t.updateQueue, n !== null && Pc(t, n.retryQueue), n = null, e !== null && e.memoizedState !== null && e.memoizedState.cachePool !== null && (n = e.memoizedState.cachePool.pool), r = null, t.memoizedState !== null && t.memoizedState.cachePool !== null && (r = t.memoizedState.cachePool.pool), r !== n && (t.flags |= 2048), e !== null && ie(ga), null;
			case 24: return n = null, e !== null && (n = e.memoizedState.cache), t.memoizedState.cache !== n && (t.flags |= 2048), Yi(sa), Ic(t), null;
			case 25: return null;
			case 30: return null;
		}
		throw Error(i(156, t.tag));
	}
	function Rc(e, t) {
		switch (ji(t), t.tag) {
			case 1: return e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 3: return Yi(sa), fe(), e = t.flags, e & 65536 && !(e & 128) ? (t.flags = e & -65537 | 128, t) : null;
			case 26:
			case 27:
			case 5: return he(t), null;
			case 31:
				if (t.memoizedState !== null) {
					if (so(t), t.alternate === null) throw Error(i(340));
					Hi();
				}
				return e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 13:
				if (so(t), e = t.memoizedState, e !== null && e.dehydrated !== null) {
					if (t.alternate === null) throw Error(i(340));
					Hi();
				}
				return e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 19: return ie(co), null;
			case 4: return fe(), null;
			case 10: return Yi(t.type), null;
			case 22:
			case 23: return so(t), eo(), e !== null && ie(ga), e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 24: return Yi(sa), null;
			case 25: return null;
			default: return null;
		}
	}
	function zc(e, t) {
		switch (ji(t), t.tag) {
			case 3:
				Yi(sa), fe();
				break;
			case 26:
			case 27:
			case 5:
				he(t);
				break;
			case 4:
				fe();
				break;
			case 31:
				t.memoizedState !== null && so(t);
				break;
			case 13:
				so(t);
				break;
			case 19:
				ie(co);
				break;
			case 10:
				Yi(t.type);
				break;
			case 22:
			case 23:
				so(t), eo(), e !== null && ie(ga);
				break;
			case 24: Yi(sa);
		}
	}
	function Bc(e, t) {
		try {
			var n = t.updateQueue, r = n === null ? null : n.lastEffect;
			if (r !== null) {
				var i = r.next;
				n = i;
				do {
					if ((n.tag & e) === e) {
						r = void 0;
						var a = n.create, o = n.inst;
						r = a(), o.destroy = r;
					}
					n = n.next;
				} while (n !== i);
			}
		} catch (e) {
			Ju(t, t.return, e);
		}
	}
	function Vc(e, t, n) {
		try {
			var r = t.updateQueue, i = r === null ? null : r.lastEffect;
			if (i !== null) {
				var a = i.next;
				r = a;
				do {
					if ((r.tag & e) === e) {
						var o = r.inst, s = o.destroy;
						if (s !== void 0) {
							o.destroy = void 0, i = t;
							var c = n, l = s;
							try {
								l();
							} catch (e) {
								Ju(i, c, e);
							}
						}
					}
					r = r.next;
				} while (r !== a);
			}
		} catch (e) {
			Ju(t, t.return, e);
		}
	}
	function Hc(e) {
		var t = e.updateQueue;
		if (t !== null) {
			var n = e.stateNode;
			try {
				Ya(t, n);
			} catch (t) {
				Ju(e, e.return, t);
			}
		}
	}
	function Uc(e, t, n) {
		n.props = Ws(e.type, e.memoizedProps), n.state = e.memoizedState;
		try {
			n.componentWillUnmount();
		} catch (n) {
			Ju(e, t, n);
		}
	}
	function Wc(e, t) {
		try {
			var n = e.ref;
			if (n !== null) {
				switch (e.tag) {
					case 26:
					case 27:
					case 5:
						var r = e.stateNode;
						break;
					case 30:
						r = e.stateNode;
						break;
					default: r = e.stateNode;
				}
				typeof n == "function" ? e.refCleanup = n(r) : n.current = r;
			}
		} catch (n) {
			Ju(e, t, n);
		}
	}
	function Gc(e, t) {
		var n = e.ref, r = e.refCleanup;
		if (n !== null) if (typeof r == "function") try {
			r();
		} catch (n) {
			Ju(e, t, n);
		} finally {
			e.refCleanup = null, e = e.alternate, e != null && (e.refCleanup = null);
		}
		else if (typeof n == "function") try {
			n(null);
		} catch (n) {
			Ju(e, t, n);
		}
		else n.current = null;
	}
	function Kc(e) {
		var t = e.type, n = e.memoizedProps, r = e.stateNode;
		try {
			a: switch (t) {
				case "button":
				case "input":
				case "select":
				case "textarea":
					n.autoFocus && r.focus();
					break a;
				case "img": n.src ? r.src = n.src : n.srcSet && (r.srcset = n.srcSet);
			}
		} catch (t) {
			Ju(e, e.return, t);
		}
	}
	function qc(e, t, n) {
		try {
			var r = e.stateNode;
			zd(r, e.type, n, t), r[st] = t;
		} catch (t) {
			Ju(e, e.return, t);
		}
	}
	function Jc(e) {
		return e.tag === 5 || e.tag === 3 || e.tag === 26 || e.tag === 27 && tf(e.type) || e.tag === 4;
	}
	function Yc(e) {
		a: for (;;) {
			for (; e.sibling === null;) {
				if (e.return === null || Jc(e.return)) return null;
				e = e.return;
			}
			for (e.sibling.return = e.return, e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18;) {
				if (e.tag === 27 && tf(e.type) || e.flags & 2 || e.child === null || e.tag === 4) continue a;
				e.child.return = e, e = e.child;
			}
			if (!(e.flags & 2)) return e.stateNode;
		}
	}
	function Xc(e, t, n) {
		var r = e.tag;
		if (r === 5 || r === 6) e = e.stateNode, t ? (n.nodeType === 9 ? n.body : n.nodeName === "HTML" ? n.ownerDocument.body : n).insertBefore(e, t) : (t = n.nodeType === 9 ? n.body : n.nodeName === "HTML" ? n.ownerDocument.body : n, t.appendChild(e), n = n._reactRootContainer, n != null || t.onclick !== null || (t.onclick = $t));
		else if (r !== 4 && (r === 27 && tf(e.type) && (n = e.stateNode, t = null), e = e.child, e !== null)) for (Xc(e, t, n), e = e.sibling; e !== null;) Xc(e, t, n), e = e.sibling;
	}
	function Zc(e, t, n) {
		var r = e.tag;
		if (r === 5 || r === 6) e = e.stateNode, t ? n.insertBefore(e, t) : n.appendChild(e);
		else if (r !== 4 && (r === 27 && tf(e.type) && (n = e.stateNode), e = e.child, e !== null)) for (Zc(e, t, n), e = e.sibling; e !== null;) Zc(e, t, n), e = e.sibling;
	}
	function Qc(e) {
		var t = e.stateNode, n = e.memoizedProps;
		try {
			for (var r = e.type, i = t.attributes; i.length;) t.removeAttributeNode(i[0]);
			Rd(t, r, n), t[ot] = e, t[st] = n;
		} catch (t) {
			Ju(e, e.return, t);
		}
	}
	var $c = !1, el = !1, tl = !1, nl = typeof WeakSet == "function" ? WeakSet : Set, rl = null;
	function il(e, t) {
		if (e = e.containerInfo, Hd = dp, e = Dr(e), Or(e)) {
			if ("selectionStart" in e) var n = {
				start: e.selectionStart,
				end: e.selectionEnd
			};
			else a: {
				n = (n = e.ownerDocument) && n.defaultView || window;
				var r = n.getSelection && n.getSelection();
				if (r && r.rangeCount !== 0) {
					n = r.anchorNode;
					var a = r.anchorOffset, o = r.focusNode;
					r = r.focusOffset;
					try {
						n.nodeType, o.nodeType;
					} catch {
						n = null;
						break a;
					}
					var s = 0, c = -1, l = -1, u = 0, d = 0, f = e, p = null;
					b: for (;;) {
						for (var m; f !== n || a !== 0 && f.nodeType !== 3 || (c = s + a), f !== o || r !== 0 && f.nodeType !== 3 || (l = s + r), f.nodeType === 3 && (s += f.nodeValue.length), (m = f.firstChild) !== null;) p = f, f = m;
						for (;;) {
							if (f === e) break b;
							if (p === n && ++u === a && (c = s), p === o && ++d === r && (l = s), (m = f.nextSibling) !== null) break;
							f = p, p = f.parentNode;
						}
						f = m;
					}
					n = c === -1 || l === -1 ? null : {
						start: c,
						end: l
					};
				} else n = null;
			}
			n ||= {
				start: 0,
				end: 0
			};
		} else n = null;
		for (Ud = {
			focusedElem: e,
			selectionRange: n
		}, dp = !1, rl = t; rl !== null;) if (t = rl, e = t.child, t.subtreeFlags & 1028 && e !== null) e.return = t, rl = e;
		else for (; rl !== null;) {
			switch (t = rl, o = t.alternate, e = t.flags, t.tag) {
				case 0:
					if (e & 4 && (e = t.updateQueue, e = e === null ? null : e.events, e !== null)) for (n = 0; n < e.length; n++) a = e[n], a.ref.impl = a.nextImpl;
					break;
				case 11:
				case 15: break;
				case 1:
					if (e & 1024 && o !== null) {
						e = void 0, n = t, a = o.memoizedProps, o = o.memoizedState, r = n.stateNode;
						try {
							var h = Ws(n.type, a);
							e = r.getSnapshotBeforeUpdate(h, o), r.__reactInternalSnapshotBeforeUpdate = e;
						} catch (e) {
							Ju(n, n.return, e);
						}
					}
					break;
				case 3:
					if (e & 1024) {
						if (e = t.stateNode.containerInfo, n = e.nodeType, n === 9) af(e);
						else if (n === 1) switch (e.nodeName) {
							case "HEAD":
							case "HTML":
							case "BODY":
								af(e);
								break;
							default: e.textContent = "";
						}
					}
					break;
				case 5:
				case 26:
				case 27:
				case 6:
				case 4:
				case 17: break;
				default: if (e & 1024) throw Error(i(163));
			}
			if (e = t.sibling, e !== null) {
				e.return = t.return, rl = e;
				break;
			}
			rl = t.return;
		}
	}
	function al(e, t, n) {
		var r = n.flags;
		switch (n.tag) {
			case 0:
			case 11:
			case 15:
				bl(e, n), r & 4 && Bc(5, n);
				break;
			case 1:
				if (bl(e, n), r & 4) if (e = n.stateNode, t === null) try {
					e.componentDidMount();
				} catch (e) {
					Ju(n, n.return, e);
				}
				else {
					var i = Ws(n.type, t.memoizedProps);
					t = t.memoizedState;
					try {
						e.componentDidUpdate(i, t, e.__reactInternalSnapshotBeforeUpdate);
					} catch (e) {
						Ju(n, n.return, e);
					}
				}
				r & 64 && Hc(n), r & 512 && Wc(n, n.return);
				break;
			case 3:
				if (bl(e, n), r & 64 && (e = n.updateQueue, e !== null)) {
					if (t = null, n.child !== null) switch (n.child.tag) {
						case 27:
						case 5:
							t = n.child.stateNode;
							break;
						case 1: t = n.child.stateNode;
					}
					try {
						Ya(e, t);
					} catch (e) {
						Ju(n, n.return, e);
					}
				}
				break;
			case 27: t === null && r & 4 && Qc(n);
			case 26:
			case 5:
				bl(e, n), t === null && r & 4 && Kc(n), r & 512 && Wc(n, n.return);
				break;
			case 12:
				bl(e, n);
				break;
			case 31:
				bl(e, n), r & 4 && dl(e, n);
				break;
			case 13:
				bl(e, n), r & 4 && fl(e, n), r & 64 && (e = n.memoizedState, e !== null && (e = e.dehydrated, e !== null && (n = Qu.bind(null, n), df(e, n))));
				break;
			case 22:
				if (r = n.memoizedState !== null || $c, !r) {
					t = t !== null && t.memoizedState !== null || el, i = $c;
					var a = el;
					$c = r, (el = t) && !a ? Sl(e, n, (n.subtreeFlags & 8772) != 0) : bl(e, n), $c = i, el = a;
				}
				break;
			case 30: break;
			default: bl(e, n);
		}
	}
	function ol(e) {
		var t = e.alternate;
		t !== null && (e.alternate = null, ol(t)), e.child = null, e.deletions = null, e.sibling = null, e.tag === 5 && (t = e.stateNode, t !== null && mt(t)), e.stateNode = null, e.return = null, e.dependencies = null, e.memoizedProps = null, e.memoizedState = null, e.pendingProps = null, e.stateNode = null, e.updateQueue = null;
	}
	var sl = null, cl = !1;
	function ll(e, t, n) {
		for (n = n.child; n !== null;) ul(e, t, n), n = n.sibling;
	}
	function ul(e, t, n) {
		if (Ie && typeof Ie.onCommitFiberUnmount == "function") try {
			Ie.onCommitFiberUnmount(Fe, n);
		} catch {}
		switch (n.tag) {
			case 26:
				el || Gc(n, t), ll(e, t, n), n.memoizedState ? n.memoizedState.count-- : n.stateNode && (n = n.stateNode, n.parentNode.removeChild(n));
				break;
			case 27:
				el || Gc(n, t);
				var r = sl, i = cl;
				tf(n.type) && (sl = n.stateNode, cl = !1), ll(e, t, n), _f(n.stateNode), sl = r, cl = i;
				break;
			case 5: el || Gc(n, t);
			case 6:
				if (r = sl, i = cl, sl = null, ll(e, t, n), sl = r, cl = i, sl !== null) if (cl) try {
					(sl.nodeType === 9 ? sl.body : sl.nodeName === "HTML" ? sl.ownerDocument.body : sl).removeChild(n.stateNode);
				} catch (e) {
					Ju(n, t, e);
				}
				else try {
					sl.removeChild(n.stateNode);
				} catch (e) {
					Ju(n, t, e);
				}
				break;
			case 18:
				sl !== null && (cl ? (e = sl, nf(e.nodeType === 9 ? e.body : e.nodeName === "HTML" ? e.ownerDocument.body : e, n.stateNode), Lp(e)) : nf(sl, n.stateNode));
				break;
			case 4:
				r = sl, i = cl, sl = n.stateNode.containerInfo, cl = !0, ll(e, t, n), sl = r, cl = i;
				break;
			case 0:
			case 11:
			case 14:
			case 15:
				Vc(2, n, t), el || Vc(4, n, t), ll(e, t, n);
				break;
			case 1:
				el || (Gc(n, t), r = n.stateNode, typeof r.componentWillUnmount == "function" && Uc(n, t, r)), ll(e, t, n);
				break;
			case 21:
				ll(e, t, n);
				break;
			case 22:
				el = (r = el) || n.memoizedState !== null, ll(e, t, n), el = r;
				break;
			default: ll(e, t, n);
		}
	}
	function dl(e, t) {
		if (t.memoizedState === null && (e = t.alternate, e !== null && (e = e.memoizedState, e !== null))) {
			e = e.dehydrated;
			try {
				Lp(e);
			} catch (e) {
				Ju(t, t.return, e);
			}
		}
	}
	function fl(e, t) {
		if (t.memoizedState === null && (e = t.alternate, e !== null && (e = e.memoizedState, e !== null && (e = e.dehydrated, e !== null)))) try {
			Lp(e);
		} catch (e) {
			Ju(t, t.return, e);
		}
	}
	function pl(e) {
		switch (e.tag) {
			case 31:
			case 13:
			case 19:
				var t = e.stateNode;
				return t === null && (t = e.stateNode = new nl()), t;
			case 22: return e = e.stateNode, t = e._retryCache, t === null && (t = e._retryCache = new nl()), t;
			default: throw Error(i(435, e.tag));
		}
	}
	function ml(e, t) {
		var n = pl(e);
		t.forEach(function(t) {
			if (!n.has(t)) {
				n.add(t);
				var r = $u.bind(null, e, t);
				t.then(r, r);
			}
		});
	}
	function hl(e, t) {
		var n = t.deletions;
		if (n !== null) for (var r = 0; r < n.length; r++) {
			var a = n[r], o = e, s = t, c = s;
			a: for (; c !== null;) {
				switch (c.tag) {
					case 27:
						if (tf(c.type)) {
							sl = c.stateNode, cl = !1;
							break a;
						}
						break;
					case 5:
						sl = c.stateNode, cl = !1;
						break a;
					case 3:
					case 4:
						sl = c.stateNode.containerInfo, cl = !0;
						break a;
				}
				c = c.return;
			}
			if (sl === null) throw Error(i(160));
			ul(o, s, a), sl = null, cl = !1, o = a.alternate, o !== null && (o.return = null), a.return = null;
		}
		if (t.subtreeFlags & 13886) for (t = t.child; t !== null;) _l(t, e), t = t.sibling;
	}
	var gl = null;
	function _l(e, t) {
		var n = e.alternate, r = e.flags;
		switch (e.tag) {
			case 0:
			case 11:
			case 14:
			case 15:
				hl(t, e), vl(e), r & 4 && (Vc(3, e, e.return), Bc(3, e), Vc(5, e, e.return));
				break;
			case 1:
				hl(t, e), vl(e), r & 512 && (el || n === null || Gc(n, n.return)), r & 64 && $c && (e = e.updateQueue, e !== null && (r = e.callbacks, r !== null && (n = e.shared.hiddenCallbacks, e.shared.hiddenCallbacks = n === null ? r : n.concat(r))));
				break;
			case 26:
				var a = gl;
				if (hl(t, e), vl(e), r & 512 && (el || n === null || Gc(n, n.return)), r & 4) {
					var o = n === null ? null : n.memoizedState;
					if (r = e.memoizedState, n === null) if (r === null) if (e.stateNode === null) {
						a: {
							r = e.type, n = e.memoizedProps, a = a.ownerDocument || a;
							b: switch (r) {
								case "title":
									o = a.getElementsByTagName("title")[0], (!o || o[pt] || o[ot] || o.namespaceURI === "http://www.w3.org/2000/svg" || o.hasAttribute("itemprop")) && (o = a.createElement(r), a.head.insertBefore(o, a.querySelector("head > title"))), Rd(o, r, n), o[ot] = e, yt(o), r = o;
									break a;
								case "link":
									var s = Gf("link", "href", a).get(r + (n.href || ""));
									if (s) {
										for (var c = 0; c < s.length; c++) if (o = s[c], o.getAttribute("href") === (n.href == null || n.href === "" ? null : n.href) && o.getAttribute("rel") === (n.rel == null ? null : n.rel) && o.getAttribute("title") === (n.title == null ? null : n.title) && o.getAttribute("crossorigin") === (n.crossOrigin == null ? null : n.crossOrigin)) {
											s.splice(c, 1);
											break b;
										}
									}
									o = a.createElement(r), Rd(o, r, n), a.head.appendChild(o);
									break;
								case "meta":
									if (s = Gf("meta", "content", a).get(r + (n.content || ""))) {
										for (c = 0; c < s.length; c++) if (o = s[c], o.getAttribute("content") === (n.content == null ? null : "" + n.content) && o.getAttribute("name") === (n.name == null ? null : n.name) && o.getAttribute("property") === (n.property == null ? null : n.property) && o.getAttribute("http-equiv") === (n.httpEquiv == null ? null : n.httpEquiv) && o.getAttribute("charset") === (n.charSet == null ? null : n.charSet)) {
											s.splice(c, 1);
											break b;
										}
									}
									o = a.createElement(r), Rd(o, r, n), a.head.appendChild(o);
									break;
								default: throw Error(i(468, r));
							}
							o[ot] = e, yt(o), r = o;
						}
						e.stateNode = r;
					} else Kf(a, e.type, e.stateNode);
					else e.stateNode = Bf(a, r, e.memoizedProps);
					else o === r ? r === null && e.stateNode !== null && qc(e, e.memoizedProps, n.memoizedProps) : (o === null ? n.stateNode !== null && (n = n.stateNode, n.parentNode.removeChild(n)) : o.count--, r === null ? Kf(a, e.type, e.stateNode) : Bf(a, r, e.memoizedProps));
				}
				break;
			case 27:
				hl(t, e), vl(e), r & 512 && (el || n === null || Gc(n, n.return)), n !== null && r & 4 && qc(e, e.memoizedProps, n.memoizedProps);
				break;
			case 5:
				if (hl(t, e), vl(e), r & 512 && (el || n === null || Gc(n, n.return)), e.flags & 32) {
					a = e.stateNode;
					try {
						Gt(a, "");
					} catch (t) {
						Ju(e, e.return, t);
					}
				}
				r & 4 && e.stateNode != null && (a = e.memoizedProps, qc(e, a, n === null ? a : n.memoizedProps)), r & 1024 && (tl = !0);
				break;
			case 6:
				if (hl(t, e), vl(e), r & 4) {
					if (e.stateNode === null) throw Error(i(162));
					r = e.memoizedProps, n = e.stateNode;
					try {
						n.nodeValue = r;
					} catch (t) {
						Ju(e, e.return, t);
					}
				}
				break;
			case 3:
				if (Wf = null, a = gl, gl = bf(t.containerInfo), hl(t, e), gl = a, vl(e), r & 4 && n !== null && n.memoizedState.isDehydrated) try {
					Lp(t.containerInfo);
				} catch (t) {
					Ju(e, e.return, t);
				}
				tl && (tl = !1, yl(e));
				break;
			case 4:
				r = gl, gl = bf(e.stateNode.containerInfo), hl(t, e), vl(e), gl = r;
				break;
			case 12:
				hl(t, e), vl(e);
				break;
			case 31:
				hl(t, e), vl(e), r & 4 && (r = e.updateQueue, r !== null && (e.updateQueue = null, ml(e, r)));
				break;
			case 13:
				hl(t, e), vl(e), e.child.flags & 8192 && e.memoizedState !== null != (n !== null && n.memoizedState !== null) && (nu = Ee()), r & 4 && (r = e.updateQueue, r !== null && (e.updateQueue = null, ml(e, r)));
				break;
			case 22:
				a = e.memoizedState !== null;
				var l = n !== null && n.memoizedState !== null, u = $c, d = el;
				if ($c = u || a, el = d || l, hl(t, e), el = d, $c = u, vl(e), r & 8192) a: for (t = e.stateNode, t._visibility = a ? t._visibility & -2 : t._visibility | 1, a && (n === null || l || $c || el || xl(e)), n = null, t = e;;) {
					if (t.tag === 5 || t.tag === 26) {
						if (n === null) {
							l = n = t;
							try {
								if (o = l.stateNode, a) s = o.style, typeof s.setProperty == "function" ? s.setProperty("display", "none", "important") : s.display = "none";
								else {
									c = l.stateNode;
									var f = l.memoizedProps.style, p = f != null && f.hasOwnProperty("display") ? f.display : null;
									c.style.display = p == null || typeof p == "boolean" ? "" : ("" + p).trim();
								}
							} catch (e) {
								Ju(l, l.return, e);
							}
						}
					} else if (t.tag === 6) {
						if (n === null) {
							l = t;
							try {
								l.stateNode.nodeValue = a ? "" : l.memoizedProps;
							} catch (e) {
								Ju(l, l.return, e);
							}
						}
					} else if (t.tag === 18) {
						if (n === null) {
							l = t;
							try {
								var m = l.stateNode;
								a ? rf(m, !0) : rf(l.stateNode, !1);
							} catch (e) {
								Ju(l, l.return, e);
							}
						}
					} else if ((t.tag !== 22 && t.tag !== 23 || t.memoizedState === null || t === e) && t.child !== null) {
						t.child.return = t, t = t.child;
						continue;
					}
					if (t === e) break a;
					for (; t.sibling === null;) {
						if (t.return === null || t.return === e) break a;
						n === t && (n = null), t = t.return;
					}
					n === t && (n = null), t.sibling.return = t.return, t = t.sibling;
				}
				r & 4 && (r = e.updateQueue, r !== null && (n = r.retryQueue, n !== null && (r.retryQueue = null, ml(e, n))));
				break;
			case 19:
				hl(t, e), vl(e), r & 4 && (r = e.updateQueue, r !== null && (e.updateQueue = null, ml(e, r)));
				break;
			case 30: break;
			case 21: break;
			default: hl(t, e), vl(e);
		}
	}
	function vl(e) {
		var t = e.flags;
		if (t & 2) {
			try {
				for (var n, r = e.return; r !== null;) {
					if (Jc(r)) {
						n = r;
						break;
					}
					r = r.return;
				}
				if (n == null) throw Error(i(160));
				switch (n.tag) {
					case 27:
						var a = n.stateNode;
						Zc(e, Yc(e), a);
						break;
					case 5:
						var o = n.stateNode;
						n.flags & 32 && (Gt(o, ""), n.flags &= -33), Zc(e, Yc(e), o);
						break;
					case 3:
					case 4:
						var s = n.stateNode.containerInfo;
						Xc(e, Yc(e), s);
						break;
					default: throw Error(i(161));
				}
			} catch (t) {
				Ju(e, e.return, t);
			}
			e.flags &= -3;
		}
		t & 4096 && (e.flags &= -4097);
	}
	function yl(e) {
		if (e.subtreeFlags & 1024) for (e = e.child; e !== null;) {
			var t = e;
			yl(t), t.tag === 5 && t.flags & 1024 && t.stateNode.reset(), e = e.sibling;
		}
	}
	function bl(e, t) {
		if (t.subtreeFlags & 8772) for (t = t.child; t !== null;) al(e, t.alternate, t), t = t.sibling;
	}
	function xl(e) {
		for (e = e.child; e !== null;) {
			var t = e;
			switch (t.tag) {
				case 0:
				case 11:
				case 14:
				case 15:
					Vc(4, t, t.return), xl(t);
					break;
				case 1:
					Gc(t, t.return);
					var n = t.stateNode;
					typeof n.componentWillUnmount == "function" && Uc(t, t.return, n), xl(t);
					break;
				case 27: _f(t.stateNode);
				case 26:
				case 5:
					Gc(t, t.return), xl(t);
					break;
				case 22:
					t.memoizedState === null && xl(t);
					break;
				case 30:
					xl(t);
					break;
				default: xl(t);
			}
			e = e.sibling;
		}
	}
	function Sl(e, t, n) {
		for (n &&= (t.subtreeFlags & 8772) != 0, t = t.child; t !== null;) {
			var r = t.alternate, i = e, a = t, o = a.flags;
			switch (a.tag) {
				case 0:
				case 11:
				case 15:
					Sl(i, a, n), Bc(4, a);
					break;
				case 1:
					if (Sl(i, a, n), r = a, i = r.stateNode, typeof i.componentDidMount == "function") try {
						i.componentDidMount();
					} catch (e) {
						Ju(r, r.return, e);
					}
					if (r = a, i = r.updateQueue, i !== null) {
						var s = r.stateNode;
						try {
							var c = i.shared.hiddenCallbacks;
							if (c !== null) for (i.shared.hiddenCallbacks = null, i = 0; i < c.length; i++) Ja(c[i], s);
						} catch (e) {
							Ju(r, r.return, e);
						}
					}
					n && o & 64 && Hc(a), Wc(a, a.return);
					break;
				case 27: Qc(a);
				case 26:
				case 5:
					Sl(i, a, n), n && r === null && o & 4 && Kc(a), Wc(a, a.return);
					break;
				case 12:
					Sl(i, a, n);
					break;
				case 31:
					Sl(i, a, n), n && o & 4 && dl(i, a);
					break;
				case 13:
					Sl(i, a, n), n && o & 4 && fl(i, a);
					break;
				case 22:
					a.memoizedState === null && Sl(i, a, n), Wc(a, a.return);
					break;
				case 30: break;
				default: Sl(i, a, n);
			}
			t = t.sibling;
		}
	}
	function Cl(e, t) {
		var n = null;
		e !== null && e.memoizedState !== null && e.memoizedState.cachePool !== null && (n = e.memoizedState.cachePool.pool), e = null, t.memoizedState !== null && t.memoizedState.cachePool !== null && (e = t.memoizedState.cachePool.pool), e !== n && (e != null && e.refCount++, n != null && la(n));
	}
	function wl(e, t) {
		e = null, t.alternate !== null && (e = t.alternate.memoizedState.cache), t = t.memoizedState.cache, t !== e && (t.refCount++, e != null && la(e));
	}
	function Tl(e, t, n, r) {
		if (t.subtreeFlags & 10256) for (t = t.child; t !== null;) El(e, t, n, r), t = t.sibling;
	}
	function El(e, t, n, r) {
		var i = t.flags;
		switch (t.tag) {
			case 0:
			case 11:
			case 15:
				Tl(e, t, n, r), i & 2048 && Bc(9, t);
				break;
			case 1:
				Tl(e, t, n, r);
				break;
			case 3:
				Tl(e, t, n, r), i & 2048 && (e = null, t.alternate !== null && (e = t.alternate.memoizedState.cache), t = t.memoizedState.cache, t !== e && (t.refCount++, e != null && la(e)));
				break;
			case 12:
				if (i & 2048) {
					Tl(e, t, n, r), e = t.stateNode;
					try {
						var a = t.memoizedProps, o = a.id, s = a.onPostCommit;
						typeof s == "function" && s(o, t.alternate === null ? "mount" : "update", e.passiveEffectDuration, -0);
					} catch (e) {
						Ju(t, t.return, e);
					}
				} else Tl(e, t, n, r);
				break;
			case 31:
				Tl(e, t, n, r);
				break;
			case 13:
				Tl(e, t, n, r);
				break;
			case 23: break;
			case 22:
				a = t.stateNode, o = t.alternate, t.memoizedState === null ? a._visibility & 2 ? Tl(e, t, n, r) : (a._visibility |= 2, Dl(e, t, n, r, (t.subtreeFlags & 10256) != 0 || !1)) : a._visibility & 2 ? Tl(e, t, n, r) : Ol(e, t), i & 2048 && Cl(o, t);
				break;
			case 24:
				Tl(e, t, n, r), i & 2048 && wl(t.alternate, t);
				break;
			default: Tl(e, t, n, r);
		}
	}
	function Dl(e, t, n, r, i) {
		for (i &&= (t.subtreeFlags & 10256) != 0 || !1, t = t.child; t !== null;) {
			var a = e, o = t, s = n, c = r, l = o.flags;
			switch (o.tag) {
				case 0:
				case 11:
				case 15:
					Dl(a, o, s, c, i), Bc(8, o);
					break;
				case 23: break;
				case 22:
					var u = o.stateNode;
					o.memoizedState === null ? (u._visibility |= 2, Dl(a, o, s, c, i)) : u._visibility & 2 ? Dl(a, o, s, c, i) : Ol(a, o), i && l & 2048 && Cl(o.alternate, o);
					break;
				case 24:
					Dl(a, o, s, c, i), i && l & 2048 && wl(o.alternate, o);
					break;
				default: Dl(a, o, s, c, i);
			}
			t = t.sibling;
		}
	}
	function Ol(e, t) {
		if (t.subtreeFlags & 10256) for (t = t.child; t !== null;) {
			var n = e, r = t, i = r.flags;
			switch (r.tag) {
				case 22:
					Ol(n, r), i & 2048 && Cl(r.alternate, r);
					break;
				case 24:
					Ol(n, r), i & 2048 && wl(r.alternate, r);
					break;
				default: Ol(n, r);
			}
			t = t.sibling;
		}
	}
	var kl = 8192;
	function Al(e, t, n) {
		if (e.subtreeFlags & kl) for (e = e.child; e !== null;) jl(e, t, n), e = e.sibling;
	}
	function jl(e, t, n) {
		switch (e.tag) {
			case 26:
				Al(e, t, n), e.flags & kl && e.memoizedState !== null && Yf(n, gl, e.memoizedState, e.memoizedProps);
				break;
			case 5:
				Al(e, t, n);
				break;
			case 3:
			case 4:
				var r = gl;
				gl = bf(e.stateNode.containerInfo), Al(e, t, n), gl = r;
				break;
			case 22:
				e.memoizedState === null && (r = e.alternate, r !== null && r.memoizedState !== null ? (r = kl, kl = 16777216, Al(e, t, n), kl = r) : Al(e, t, n));
				break;
			default: Al(e, t, n);
		}
	}
	function Ml(e) {
		var t = e.alternate;
		if (t !== null && (e = t.child, e !== null)) {
			t.child = null;
			do
				t = e.sibling, e.sibling = null, e = t;
			while (e !== null);
		}
	}
	function Nl(e) {
		var t = e.deletions;
		if (e.flags & 16) {
			if (t !== null) for (var n = 0; n < t.length; n++) {
				var r = t[n];
				rl = r, Il(r, e);
			}
			Ml(e);
		}
		if (e.subtreeFlags & 10256) for (e = e.child; e !== null;) Pl(e), e = e.sibling;
	}
	function Pl(e) {
		switch (e.tag) {
			case 0:
			case 11:
			case 15:
				Nl(e), e.flags & 2048 && Vc(9, e, e.return);
				break;
			case 3:
				Nl(e);
				break;
			case 12:
				Nl(e);
				break;
			case 22:
				var t = e.stateNode;
				e.memoizedState !== null && t._visibility & 2 && (e.return === null || e.return.tag !== 13) ? (t._visibility &= -3, Fl(e)) : Nl(e);
				break;
			default: Nl(e);
		}
	}
	function Fl(e) {
		var t = e.deletions;
		if (e.flags & 16) {
			if (t !== null) for (var n = 0; n < t.length; n++) {
				var r = t[n];
				rl = r, Il(r, e);
			}
			Ml(e);
		}
		for (e = e.child; e !== null;) {
			switch (t = e, t.tag) {
				case 0:
				case 11:
				case 15:
					Vc(8, t, t.return), Fl(t);
					break;
				case 22:
					n = t.stateNode, n._visibility & 2 && (n._visibility &= -3, Fl(t));
					break;
				default: Fl(t);
			}
			e = e.sibling;
		}
	}
	function Il(e, t) {
		for (; rl !== null;) {
			var n = rl;
			switch (n.tag) {
				case 0:
				case 11:
				case 15:
					Vc(8, n, t);
					break;
				case 23:
				case 22:
					if (n.memoizedState !== null && n.memoizedState.cachePool !== null) {
						var r = n.memoizedState.cachePool.pool;
						r != null && r.refCount++;
					}
					break;
				case 24: la(n.memoizedState.cache);
			}
			if (r = n.child, r !== null) r.return = n, rl = r;
			else a: for (n = e; rl !== null;) {
				r = rl;
				var i = r.sibling, a = r.return;
				if (ol(r), r === n) {
					rl = null;
					break a;
				}
				if (i !== null) {
					i.return = a, rl = i;
					break a;
				}
				rl = a;
			}
		}
	}
	var Ll = {
		getCacheForType: function(e) {
			var t = ta(sa), n = t.data.get(e);
			return n === void 0 && (n = e(), t.data.set(e, n)), n;
		},
		cacheSignal: function() {
			return ta(sa).controller.signal;
		}
	}, Rl = typeof WeakMap == "function" ? WeakMap : Map, zl = 0, Bl = null, K = null, q = 0, Vl = 0, Hl = null, Ul = !1, Wl = !1, Gl = !1, Kl = 0, ql = 0, Jl = 0, Yl = 0, Xl = 0, Zl = 0, Ql = 0, $l = null, eu = null, tu = !1, nu = 0, ru = 0, iu = Infinity, au = null, ou = null, su = 0, cu = null, lu = null, uu = 0, du = 0, fu = null, pu = null, mu = 0, hu = null;
	function gu() {
		return zl & 2 && q !== 0 ? q & -q : M.T === null ? R() : hd();
	}
	function _u() {
		if (Zl === 0) if (!(q & 536870912) || z) {
			var e = Ue;
			Ue <<= 1, !(Ue & 3932160) && (Ue = 262144), Zl = e;
		} else Zl = 536870912;
		return e = to.current, e !== null && (e.flags |= 32), Zl;
	}
	function vu(e, t, n) {
		(e === Bl && (Vl === 2 || Vl === 9) || e.cancelPendingCommit !== null) && (Tu(e, 0), Su(e, q, Zl, !1)), Ze(e, n), (!(zl & 2) || e !== Bl) && (e === Bl && (!(zl & 2) && (Yl |= n), ql === 4 && Su(e, q, Zl, !1)), sd(e));
	}
	function yu(e, t, n) {
		if (zl & 6) throw Error(i(327));
		var r = !n && (t & 127) == 0 && (t & e.expiredLanes) === 0 || qe(e, t), a = r ? Nu(e, t) : ju(e, t, !0), o = r;
		do {
			if (a === 0) {
				Wl && !r && Su(e, t, 0, !1);
				break;
			} else {
				if (n = e.current.alternate, o && !xu(n)) {
					a = ju(e, t, !1), o = !1;
					continue;
				}
				if (a === 2) {
					if (o = t, e.errorRecoveryDisabledLanes & o) var s = 0;
					else s = e.pendingLanes & -536870913, s = s === 0 ? s & 536870912 ? 536870912 : 0 : s;
					if (s !== 0) {
						t = s;
						a: {
							var c = e;
							a = $l;
							var l = c.current.memoizedState.isDehydrated;
							if (l && (Tu(c, s).flags |= 256), s = ju(c, s, !1), s !== 2) {
								if (Gl && !l) {
									c.errorRecoveryDisabledLanes |= o, Yl |= o, a = 4;
									break a;
								}
								o = eu, eu = a, o !== null && (eu === null ? eu = o : eu.push.apply(eu, o));
							}
							a = s;
						}
						if (o = !1, a !== 2) continue;
					}
				}
				if (a === 1) {
					Tu(e, 0), Su(e, t, 0, !0);
					break;
				}
				a: {
					switch (r = e, o = a, o) {
						case 0:
						case 1: throw Error(i(345));
						case 4: if ((t & 4194048) !== t) break;
						case 6:
							Su(r, t, Zl, !Ul);
							break a;
						case 2:
							eu = null;
							break;
						case 3:
						case 5: break;
						default: throw Error(i(329));
					}
					if ((t & 62914560) === t && (a = nu + 300 - Ee(), 10 < a)) {
						if (Su(r, t, Zl, !Ul), Ke(r, 0, !0) !== 0) break a;
						uu = t, r.timeoutHandle = Xd(bu.bind(null, r, n, eu, au, tu, t, Zl, Yl, Ql, Ul, o, "Throttled", -0, 0), a);
						break a;
					}
					bu(r, n, eu, au, tu, t, Zl, Yl, Ql, Ul, o, null, -0, 0);
				}
			}
			break;
		} while (1);
		sd(e);
	}
	function bu(e, t, n, r, i, a, o, s, c, l, u, d, f, p) {
		if (e.timeoutHandle = -1, d = t.subtreeFlags, d & 8192 || (d & 16785408) == 16785408) {
			d = {
				stylesheets: null,
				count: 0,
				imgCount: 0,
				imgBytes: 0,
				suspenseyImages: [],
				waitingForImages: !0,
				waitingForViewTransition: !1,
				unsuspend: $t
			}, jl(t, a, d);
			var m = (a & 62914560) === a ? nu - Ee() : (a & 4194048) === a ? ru - Ee() : 0;
			if (m = Zf(d, m), m !== null) {
				uu = a, e.cancelPendingCommit = m(Bu.bind(null, e, t, a, n, r, i, o, s, c, u, d, null, f, p)), Su(e, a, o, !l);
				return;
			}
		}
		Bu(e, t, a, n, r, i, o, s, c);
	}
	function xu(e) {
		for (var t = e;;) {
			var n = t.tag;
			if ((n === 0 || n === 11 || n === 15) && t.flags & 16384 && (n = t.updateQueue, n !== null && (n = n.stores, n !== null))) for (var r = 0; r < n.length; r++) {
				var i = n[r], a = i.getSnapshot;
				i = i.value;
				try {
					if (!Sr(a(), i)) return !1;
				} catch {
					return !1;
				}
			}
			if (n = t.child, t.subtreeFlags & 16384 && n !== null) n.return = t, t = n;
			else {
				if (t === e) break;
				for (; t.sibling === null;) {
					if (t.return === null || t.return === e) return !0;
					t = t.return;
				}
				t.sibling.return = t.return, t = t.sibling;
			}
		}
		return !0;
	}
	function Su(e, t, n, r) {
		t &= ~Xl, t &= ~Yl, e.suspendedLanes |= t, e.pingedLanes &= ~t, r && (e.warmLanes |= t), r = e.expirationTimes;
		for (var i = t; 0 < i;) {
			var a = 31 - Re(i), o = 1 << a;
			r[a] = -1, i &= ~o;
		}
		n !== 0 && $e(e, n, t);
	}
	function Cu() {
		return zl & 6 ? !0 : (cd(0, !1), !1);
	}
	function wu() {
		if (K !== null) {
			if (Vl === 0) var e = K.return;
			else e = K, qi = Ki = null, ko(e), Aa = null, ja = 0, e = K;
			for (; e !== null;) zc(e.alternate, e), e = e.return;
			K = null;
		}
	}
	function Tu(e, t) {
		var n = e.timeoutHandle;
		n !== -1 && (e.timeoutHandle = -1, Zd(n)), n = e.cancelPendingCommit, n !== null && (e.cancelPendingCommit = null, n()), uu = 0, wu(), Bl = e, K = n = ui(e.current, null), q = t, Vl = 0, Hl = null, Ul = !1, Wl = qe(e, t), Gl = !1, Ql = Zl = Xl = Yl = Jl = ql = 0, eu = $l = null, tu = !1, t & 8 && (t |= t & 32);
		var r = e.entangledLanes;
		if (r !== 0) for (e = e.entanglements, r &= t; 0 < r;) {
			var i = 31 - Re(r), a = 1 << i;
			t |= e[i], r &= ~a;
		}
		return Kl = t, ei(), n;
	}
	function Eu(e, t) {
		H = null, M.H = Is, t === ba || t === Sa ? (t = Oa(), Vl = 3) : t === xa ? (t = Oa(), Vl = 4) : Vl = t === ec ? 8 : typeof t == "object" && t && typeof t.then == "function" ? 6 : 1, Hl = t, K === null && (ql = 1, Js(e, vi(t, e.current)));
	}
	function Du() {
		var e = to.current;
		return e === null ? !0 : (q & 4194048) === q ? no === null : (q & 62914560) === q || q & 536870912 ? e === no : !1;
	}
	function Ou() {
		var e = M.H;
		return M.H = Is, e === null ? Is : e;
	}
	function ku() {
		var e = M.A;
		return M.A = Ll, e;
	}
	function Au() {
		ql = 4, Ul || (q & 4194048) !== q && to.current !== null || (Wl = !0), !(Jl & 134217727) && !(Yl & 134217727) || Bl === null || Su(Bl, q, Zl, !1);
	}
	function ju(e, t, n) {
		var r = zl;
		zl |= 2;
		var i = Ou(), a = ku();
		(Bl !== e || q !== t) && (au = null, Tu(e, t)), t = !1;
		var o = ql;
		a: do
			try {
				if (Vl !== 0 && K !== null) {
					var s = K, c = Hl;
					switch (Vl) {
						case 8:
							wu(), o = 6;
							break a;
						case 3:
						case 2:
						case 9:
						case 6:
							to.current === null && (t = !0);
							var l = Vl;
							if (Vl = 0, Hl = null, Lu(e, s, c, l), n && Wl) {
								o = 0;
								break a;
							}
							break;
						default: l = Vl, Vl = 0, Hl = null, Lu(e, s, c, l);
					}
				}
				Mu(), o = ql;
				break;
			} catch (t) {
				Eu(e, t);
			}
		while (1);
		return t && e.shellSuspendCounter++, qi = Ki = null, zl = r, M.H = i, M.A = a, K === null && (Bl = null, q = 0, ei()), o;
	}
	function Mu() {
		for (; K !== null;) Fu(K);
	}
	function Nu(e, t) {
		var n = zl;
		zl |= 2;
		var r = Ou(), a = ku();
		Bl !== e || q !== t ? (au = null, iu = Ee() + 500, Tu(e, t)) : Wl = qe(e, t);
		a: do
			try {
				if (Vl !== 0 && K !== null) {
					t = K;
					var o = Hl;
					b: switch (Vl) {
						case 1:
							Vl = 0, Hl = null, Lu(e, t, o, 1);
							break;
						case 2:
						case 9:
							if (wa(o)) {
								Vl = 0, Hl = null, Iu(t);
								break;
							}
							t = function() {
								Vl !== 2 && Vl !== 9 || Bl !== e || (Vl = 7), sd(e);
							}, o.then(t, t);
							break a;
						case 3:
							Vl = 7;
							break a;
						case 4:
							Vl = 5;
							break a;
						case 7:
							wa(o) ? (Vl = 0, Hl = null, Iu(t)) : (Vl = 0, Hl = null, Lu(e, t, o, 7));
							break;
						case 5:
							var s = null;
							switch (K.tag) {
								case 26: s = K.memoizedState;
								case 5:
								case 27:
									var c = K;
									if (s ? Jf(s) : c.stateNode.complete) {
										Vl = 0, Hl = null;
										var l = c.sibling;
										if (l !== null) K = l;
										else {
											var u = c.return;
											u === null ? K = null : (K = u, Ru(u));
										}
										break b;
									}
							}
							Vl = 0, Hl = null, Lu(e, t, o, 5);
							break;
						case 6:
							Vl = 0, Hl = null, Lu(e, t, o, 6);
							break;
						case 8:
							wu(), ql = 6;
							break a;
						default: throw Error(i(462));
					}
				}
				Pu();
				break;
			} catch (t) {
				Eu(e, t);
			}
		while (1);
		return qi = Ki = null, M.H = r, M.A = a, zl = n, K === null ? (Bl = null, q = 0, ei(), ql) : 0;
	}
	function Pu() {
		for (; K !== null && !we();) Fu(K);
	}
	function Fu(e) {
		var t = Ac(e.alternate, e, Kl);
		e.memoizedProps = e.pendingProps, t === null ? Ru(e) : K = t;
	}
	function Iu(e) {
		var t = e, n = t.alternate;
		switch (t.tag) {
			case 15:
			case 0:
				t = mc(n, t, t.pendingProps, t.type, void 0, q);
				break;
			case 11:
				t = mc(n, t, t.pendingProps, t.type.render, t.ref, q);
				break;
			case 5: ko(t);
			default: zc(n, t), t = K = di(t, Kl), t = Ac(n, t, Kl);
		}
		e.memoizedProps = e.pendingProps, t === null ? Ru(e) : K = t;
	}
	function Lu(e, t, n, r) {
		qi = Ki = null, ko(t), Aa = null, ja = 0;
		var i = t.return;
		try {
			if ($s(e, i, t, n, q)) {
				ql = 1, Js(e, vi(n, e.current)), K = null;
				return;
			}
		} catch (t) {
			if (i !== null) throw K = i, t;
			ql = 1, Js(e, vi(n, e.current)), K = null;
			return;
		}
		t.flags & 32768 ? (z || r === 1 ? e = !0 : Wl || q & 536870912 ? e = !1 : (Ul = e = !0, (r === 2 || r === 9 || r === 3 || r === 6) && (r = to.current, r !== null && r.tag === 13 && (r.flags |= 16384))), zu(t, e)) : Ru(t);
	}
	function Ru(e) {
		var t = e;
		do {
			if (t.flags & 32768) {
				zu(t, Ul);
				return;
			}
			e = t.return;
			var n = Lc(t.alternate, t, Kl);
			if (n !== null) {
				K = n;
				return;
			}
			if (t = t.sibling, t !== null) {
				K = t;
				return;
			}
			K = t = e;
		} while (t !== null);
		ql === 0 && (ql = 5);
	}
	function zu(e, t) {
		do {
			var n = Rc(e.alternate, e);
			if (n !== null) {
				n.flags &= 32767, K = n;
				return;
			}
			if (n = e.return, n !== null && (n.flags |= 32768, n.subtreeFlags = 0, n.deletions = null), !t && (e = e.sibling, e !== null)) {
				K = e;
				return;
			}
			K = e = n;
		} while (e !== null);
		ql = 6, K = null;
	}
	function Bu(e, t, n, r, a, o, s, c, l) {
		e.cancelPendingCommit = null;
		do
			Gu();
		while (su !== 0);
		if (zl & 6) throw Error(i(327));
		if (t !== null) {
			if (t === e.current) throw Error(i(177));
			if (o = t.lanes | t.childLanes, o |= $r, Qe(e, n, o, s, c, l), e === Bl && (K = Bl = null, q = 0), lu = t, cu = e, uu = n, du = o, fu = a, pu = r, t.subtreeFlags & 10256 || t.flags & 10256 ? (e.callbackNode = null, e.callbackPriority = 0, ed(Ae, function() {
				return Ku(), null;
			})) : (e.callbackNode = null, e.callbackPriority = 0), r = (t.flags & 13878) != 0, t.subtreeFlags & 13878 || r) {
				r = M.T, M.T = null, a = N.p, N.p = 2, s = zl, zl |= 4;
				try {
					il(e, t, n);
				} finally {
					zl = s, N.p = a, M.T = r;
				}
			}
			su = 1, Vu(), Hu(), Uu();
		}
	}
	function Vu() {
		if (su === 1) {
			su = 0;
			var e = cu, t = lu, n = (t.flags & 13878) != 0;
			if (t.subtreeFlags & 13878 || n) {
				n = M.T, M.T = null;
				var r = N.p;
				N.p = 2;
				var i = zl;
				zl |= 4;
				try {
					_l(t, e);
					var a = Ud, o = Dr(e.containerInfo), s = a.focusedElem, c = a.selectionRange;
					if (o !== s && s && s.ownerDocument && Er(s.ownerDocument.documentElement, s)) {
						if (c !== null && Or(s)) {
							var l = c.start, u = c.end;
							if (u === void 0 && (u = l), "selectionStart" in s) s.selectionStart = l, s.selectionEnd = Math.min(u, s.value.length);
							else {
								var d = s.ownerDocument || document, f = d && d.defaultView || window;
								if (f.getSelection) {
									var p = f.getSelection(), m = s.textContent.length, h = Math.min(c.start, m), g = c.end === void 0 ? h : Math.min(c.end, m);
									!p.extend && h > g && (o = g, g = h, h = o);
									var _ = Tr(s, h), v = Tr(s, g);
									if (_ && v && (p.rangeCount !== 1 || p.anchorNode !== _.node || p.anchorOffset !== _.offset || p.focusNode !== v.node || p.focusOffset !== v.offset)) {
										var y = d.createRange();
										y.setStart(_.node, _.offset), p.removeAllRanges(), h > g ? (p.addRange(y), p.extend(v.node, v.offset)) : (y.setEnd(v.node, v.offset), p.addRange(y));
									}
								}
							}
						}
						for (d = [], p = s; p = p.parentNode;) p.nodeType === 1 && d.push({
							element: p,
							left: p.scrollLeft,
							top: p.scrollTop
						});
						for (typeof s.focus == "function" && s.focus(), s = 0; s < d.length; s++) {
							var b = d[s];
							b.element.scrollLeft = b.left, b.element.scrollTop = b.top;
						}
					}
					dp = !!Hd, Ud = Hd = null;
				} finally {
					zl = i, N.p = r, M.T = n;
				}
			}
			e.current = t, su = 2;
		}
	}
	function Hu() {
		if (su === 2) {
			su = 0;
			var e = cu, t = lu, n = (t.flags & 8772) != 0;
			if (t.subtreeFlags & 8772 || n) {
				n = M.T, M.T = null;
				var r = N.p;
				N.p = 2;
				var i = zl;
				zl |= 4;
				try {
					al(e, t.alternate, t);
				} finally {
					zl = i, N.p = r, M.T = n;
				}
			}
			su = 3;
		}
	}
	function Uu() {
		if (su === 4 || su === 3) {
			su = 0, Te();
			var e = cu, t = lu, n = uu, r = pu;
			t.subtreeFlags & 10256 || t.flags & 10256 ? su = 5 : (su = 0, lu = cu = null, Wu(e, e.pendingLanes));
			var i = e.pendingLanes;
			if (i === 0 && (ou = null), rt(n), t = t.stateNode, Ie && typeof Ie.onCommitFiberRoot == "function") try {
				Ie.onCommitFiberRoot(Fe, t, void 0, (t.current.flags & 128) == 128);
			} catch {}
			if (r !== null) {
				t = M.T, i = N.p, N.p = 2, M.T = null;
				try {
					for (var a = e.onRecoverableError, o = 0; o < r.length; o++) {
						var s = r[o];
						a(s.value, { componentStack: s.stack });
					}
				} finally {
					M.T = t, N.p = i;
				}
			}
			uu & 3 && Gu(), sd(e), i = e.pendingLanes, n & 261930 && i & 42 ? e === hu ? mu++ : (mu = 0, hu = e) : mu = 0, cd(0, !1);
		}
	}
	function Wu(e, t) {
		(e.pooledCacheLanes &= t) === 0 && (t = e.pooledCache, t != null && (e.pooledCache = null, la(t)));
	}
	function Gu() {
		return Vu(), Hu(), Uu(), Ku();
	}
	function Ku() {
		if (su !== 5) return !1;
		var e = cu, t = du;
		du = 0;
		var n = rt(uu), r = M.T, a = N.p;
		try {
			N.p = 32 > n ? 32 : n, M.T = null, n = fu, fu = null;
			var o = cu, s = uu;
			if (su = 0, lu = cu = null, uu = 0, zl & 6) throw Error(i(331));
			var c = zl;
			if (zl |= 4, Pl(o.current), El(o, o.current, s, n), zl = c, cd(0, !1), Ie && typeof Ie.onPostCommitFiberRoot == "function") try {
				Ie.onPostCommitFiberRoot(Fe, o);
			} catch {}
			return !0;
		} finally {
			N.p = a, M.T = r, Wu(e, t);
		}
	}
	function qu(e, t, n) {
		t = vi(n, t), t = Xs(e.stateNode, t, 2), e = Ha(e, t, 2), e !== null && (Ze(e, 2), sd(e));
	}
	function Ju(e, t, n) {
		if (e.tag === 3) qu(e, e, n);
		else for (; t !== null;) {
			if (t.tag === 3) {
				qu(t, e, n);
				break;
			} else if (t.tag === 1) {
				var r = t.stateNode;
				if (typeof t.type.getDerivedStateFromError == "function" || typeof r.componentDidCatch == "function" && (ou === null || !ou.has(r))) {
					e = vi(n, e), n = Zs(2), r = Ha(t, n, 2), r !== null && (Qs(n, r, t, e), Ze(r, 2), sd(r));
					break;
				}
			}
			t = t.return;
		}
	}
	function Yu(e, t, n) {
		var r = e.pingCache;
		if (r === null) {
			r = e.pingCache = new Rl();
			var i = /* @__PURE__ */ new Set();
			r.set(t, i);
		} else i = r.get(t), i === void 0 && (i = /* @__PURE__ */ new Set(), r.set(t, i));
		i.has(n) || (Gl = !0, i.add(n), e = Xu.bind(null, e, t, n), t.then(e, e));
	}
	function Xu(e, t, n) {
		var r = e.pingCache;
		r !== null && r.delete(t), e.pingedLanes |= e.suspendedLanes & n, e.warmLanes &= ~n, Bl === e && (q & n) === n && (ql === 4 || ql === 3 && (q & 62914560) === q && 300 > Ee() - nu ? !(zl & 2) && Tu(e, 0) : Xl |= n, Ql === q && (Ql = 0)), sd(e);
	}
	function Zu(e, t) {
		t === 0 && (t = Ye()), e = ri(e, t), e !== null && (Ze(e, t), sd(e));
	}
	function Qu(e) {
		var t = e.memoizedState, n = 0;
		t !== null && (n = t.retryLane), Zu(e, n);
	}
	function $u(e, t) {
		var n = 0;
		switch (e.tag) {
			case 31:
			case 13:
				var r = e.stateNode, a = e.memoizedState;
				a !== null && (n = a.retryLane);
				break;
			case 19:
				r = e.stateNode;
				break;
			case 22:
				r = e.stateNode._retryCache;
				break;
			default: throw Error(i(314));
		}
		r !== null && r.delete(t), Zu(e, n);
	}
	function ed(e, t) {
		return Se(e, t);
	}
	var td = null, nd = null, rd = !1, id = !1, ad = !1, od = 0;
	function sd(e) {
		e !== nd && e.next === null && (nd === null ? td = nd = e : nd = nd.next = e), id = !0, rd || (rd = !0, md());
	}
	function cd(e, t) {
		if (!ad && id) {
			ad = !0;
			do
				for (var n = !1, r = td; r !== null;) {
					if (!t) if (e !== 0) {
						var i = r.pendingLanes;
						if (i === 0) var a = 0;
						else {
							var o = r.suspendedLanes, s = r.pingedLanes;
							a = (1 << 31 - Re(42 | e) + 1) - 1, a &= i & ~(o & ~s), a = a & 201326741 ? a & 201326741 | 1 : a ? a | 2 : 0;
						}
						a !== 0 && (n = !0, pd(r, a));
					} else a = q, a = Ke(r, r === Bl ? a : 0, r.cancelPendingCommit !== null || r.timeoutHandle !== -1), !(a & 3) || qe(r, a) || (n = !0, pd(r, a));
					r = r.next;
				}
			while (n);
			ad = !1;
		}
	}
	function ld() {
		ud();
	}
	function ud() {
		id = rd = !1;
		var e = 0;
		od !== 0 && Yd() && (e = od);
		for (var t = Ee(), n = null, r = td; r !== null;) {
			var i = r.next, a = dd(r, t);
			a === 0 ? (r.next = null, n === null ? td = i : n.next = i, i === null && (nd = n)) : (n = r, (e !== 0 || a & 3) && (id = !0)), r = i;
		}
		su !== 0 && su !== 5 || cd(e, !1), od !== 0 && (od = 0);
	}
	function dd(e, t) {
		for (var n = e.suspendedLanes, r = e.pingedLanes, i = e.expirationTimes, a = e.pendingLanes & -62914561; 0 < a;) {
			var o = 31 - Re(a), s = 1 << o, c = i[o];
			c === -1 ? ((s & n) === 0 || (s & r) !== 0) && (i[o] = Je(s, t)) : c <= t && (e.expiredLanes |= s), a &= ~s;
		}
		if (t = Bl, n = q, n = Ke(e, e === t ? n : 0, e.cancelPendingCommit !== null || e.timeoutHandle !== -1), r = e.callbackNode, n === 0 || e === t && (Vl === 2 || Vl === 9) || e.cancelPendingCommit !== null) return r !== null && r !== null && Ce(r), e.callbackNode = null, e.callbackPriority = 0;
		if (!(n & 3) || qe(e, n)) {
			if (t = n & -n, t === e.callbackPriority) return t;
			switch (r !== null && Ce(r), rt(n)) {
				case 2:
				case 8:
					n = ke;
					break;
				case 32:
					n = Ae;
					break;
				case 268435456:
					n = Me;
					break;
				default: n = Ae;
			}
			return r = fd.bind(null, e), n = Se(n, r), e.callbackPriority = t, e.callbackNode = n, t;
		}
		return r !== null && r !== null && Ce(r), e.callbackPriority = 2, e.callbackNode = null, 2;
	}
	function fd(e, t) {
		if (su !== 0 && su !== 5) return e.callbackNode = null, e.callbackPriority = 0, null;
		var n = e.callbackNode;
		if (Gu() && e.callbackNode !== n) return null;
		var r = q;
		return r = Ke(e, e === Bl ? r : 0, e.cancelPendingCommit !== null || e.timeoutHandle !== -1), r === 0 ? null : (yu(e, r, t), dd(e, Ee()), e.callbackNode != null && e.callbackNode === n ? fd.bind(null, e) : null);
	}
	function pd(e, t) {
		if (Gu()) return null;
		yu(e, t, !0);
	}
	function md() {
		$d(function() {
			zl & 6 ? Se(Oe, ld) : ud();
		});
	}
	function hd() {
		if (od === 0) {
			var e = da;
			e === 0 && (e = He, He <<= 1, !(He & 261888) && (He = 256)), od = e;
		}
		return od;
	}
	function gd(e) {
		return e == null || typeof e == "symbol" || typeof e == "boolean" ? null : typeof e == "function" ? e : Qt("" + e);
	}
	function _d(e, t) {
		var n = t.ownerDocument.createElement("input");
		return n.name = t.name, n.value = t.value, e.id && n.setAttribute("form", e.id), t.parentNode.insertBefore(n, t), e = new FormData(e), n.parentNode.removeChild(n), e;
	}
	function vd(e, t, n, r, i) {
		if (t === "submit" && n && n.stateNode === i) {
			var a = gd((i[st] || null).action), o = r.submitter;
			o && (t = (t = o[st] || null) ? gd(t.formAction) : o.getAttribute("formAction"), t !== null && (a = t, o = null));
			var s = new xn("action", "action", null, r, i);
			e.push({
				event: s,
				listeners: [{
					instance: null,
					listener: function() {
						if (r.defaultPrevented) {
							if (od !== 0) {
								var e = o ? _d(i, o) : new FormData(i);
								Ss(n, {
									pending: !0,
									data: e,
									method: i.method,
									action: a
								}, null, e);
							}
						} else typeof a == "function" && (s.preventDefault(), e = o ? _d(i, o) : new FormData(i), Ss(n, {
							pending: !0,
							data: e,
							method: i.method,
							action: a
						}, a, e));
					},
					currentTarget: i
				}]
			});
		}
	}
	for (var yd = 0; yd < Jr.length; yd++) {
		var bd = Jr[yd];
		Yr(bd.toLowerCase(), "on" + (bd[0].toUpperCase() + bd.slice(1)));
	}
	Yr(Br, "onAnimationEnd"), Yr(Vr, "onAnimationIteration"), Yr(Hr, "onAnimationStart"), Yr("dblclick", "onDoubleClick"), Yr("focusin", "onFocus"), Yr("focusout", "onBlur"), Yr(Ur, "onTransitionRun"), Yr(Wr, "onTransitionStart"), Yr(Gr, "onTransitionCancel"), Yr(Kr, "onTransitionEnd"), Ct("onMouseEnter", ["mouseout", "mouseover"]), Ct("onMouseLeave", ["mouseout", "mouseover"]), Ct("onPointerEnter", ["pointerout", "pointerover"]), Ct("onPointerLeave", ["pointerout", "pointerover"]), St("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" ")), St("onSelect", "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")), St("onBeforeInput", [
		"compositionend",
		"keypress",
		"textInput",
		"paste"
	]), St("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" ")), St("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" ")), St("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
	var xd = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" "), Sd = new Set("beforetoggle cancel close invalid load scroll scrollend toggle".split(" ").concat(xd));
	function J(e, t) {
		t = (t & 4) != 0;
		for (var n = 0; n < e.length; n++) {
			var r = e[n], i = r.event;
			r = r.listeners;
			a: {
				var a = void 0;
				if (t) for (var o = r.length - 1; 0 <= o; o--) {
					var s = r[o], c = s.instance, l = s.currentTarget;
					if (s = s.listener, c !== a && i.isPropagationStopped()) break a;
					a = s, i.currentTarget = l;
					try {
						a(i);
					} catch (e) {
						Xr(e);
					}
					i.currentTarget = null, a = c;
				}
				else for (o = 0; o < r.length; o++) {
					if (s = r[o], c = s.instance, l = s.currentTarget, s = s.listener, c !== a && i.isPropagationStopped()) break a;
					a = s, i.currentTarget = l;
					try {
						a(i);
					} catch (e) {
						Xr(e);
					}
					i.currentTarget = null, a = c;
				}
			}
		}
	}
	function Y(e, t) {
		var n = t[lt];
		n === void 0 && (n = t[lt] = /* @__PURE__ */ new Set());
		var r = e + "__bubble";
		n.has(r) || (Ed(t, e, 2, !1), n.add(r));
	}
	function Cd(e, t, n) {
		var r = 0;
		t && (r |= 4), Ed(n, e, r, t);
	}
	var wd = "_reactListening" + Math.random().toString(36).slice(2);
	function Td(e) {
		if (!e[wd]) {
			e[wd] = !0, bt.forEach(function(t) {
				t !== "selectionchange" && (Sd.has(t) || Cd(t, !1, e), Cd(t, !0, e));
			});
			var t = e.nodeType === 9 ? e : e.ownerDocument;
			t === null || t[wd] || (t[wd] = !0, Cd("selectionchange", !1, t));
		}
	}
	function Ed(e, t, n, r) {
		switch (vp(t)) {
			case 2:
				var i = fp;
				break;
			case 8:
				i = pp;
				break;
			default: i = mp;
		}
		n = i.bind(null, t, n, e), i = void 0, !un || t !== "touchstart" && t !== "touchmove" && t !== "wheel" || (i = !0), r ? i === void 0 ? e.addEventListener(t, n, !0) : e.addEventListener(t, n, {
			capture: !0,
			passive: i
		}) : i === void 0 ? e.addEventListener(t, n, !1) : e.addEventListener(t, n, { passive: i });
	}
	function Dd(e, t, n, r, i) {
		var a = r;
		if (!(t & 1) && !(t & 2) && r !== null) a: for (;;) {
			if (r === null) return;
			var s = r.tag;
			if (s === 3 || s === 4) {
				var c = r.stateNode.containerInfo;
				if (c === i) break;
				if (s === 4) for (s = r.return; s !== null;) {
					var l = s.tag;
					if ((l === 3 || l === 4) && s.stateNode.containerInfo === i) return;
					s = s.return;
				}
				for (; c !== null;) {
					if (s = ht(c), s === null) return;
					if (l = s.tag, l === 5 || l === 6 || l === 26 || l === 27) {
						r = a = s;
						continue a;
					}
					c = c.parentNode;
				}
			}
			r = r.return;
		}
		sn(function() {
			var r = a, i = tn(n), s = [];
			a: {
				var c = qr.get(e);
				if (c !== void 0) {
					var l = xn, u = e;
					switch (e) {
						case "keypress": if (gn(n) === 0) break a;
						case "keydown":
						case "keyup":
							l = zn;
							break;
						case "focusin":
							u = "focus", l = An;
							break;
						case "focusout":
							u = "blur", l = An;
							break;
						case "beforeblur":
						case "afterblur":
							l = An;
							break;
						case "click": if (n.button === 2) break a;
						case "auxclick":
						case "dblclick":
						case "mousedown":
						case "mousemove":
						case "mouseup":
						case "mouseout":
						case "mouseover":
						case "contextmenu":
							l = On;
							break;
						case "drag":
						case "dragend":
						case "dragenter":
						case "dragexit":
						case "dragleave":
						case "dragover":
						case "dragstart":
						case "drop":
							l = kn;
							break;
						case "touchcancel":
						case "touchend":
						case "touchmove":
						case "touchstart":
							l = Vn;
							break;
						case Br:
						case Vr:
						case Hr:
							l = jn;
							break;
						case Kr:
							l = Hn;
							break;
						case "scroll":
						case "scrollend":
							l = Cn;
							break;
						case "wheel":
							l = Un;
							break;
						case "copy":
						case "cut":
						case "paste":
							l = Mn;
							break;
						case "gotpointercapture":
						case "lostpointercapture":
						case "pointercancel":
						case "pointerdown":
						case "pointermove":
						case "pointerout":
						case "pointerover":
						case "pointerup":
							l = Bn;
							break;
						case "toggle":
						case "beforetoggle": l = Wn;
					}
					var d = (t & 4) != 0, f = !d && (e === "scroll" || e === "scrollend"), p = d ? c === null ? null : c + "Capture" : c;
					d = [];
					for (var m = r, h; m !== null;) {
						var g = m;
						if (h = g.stateNode, g = g.tag, g !== 5 && g !== 26 && g !== 27 || h === null || p === null || (g = cn(m, p), g != null && d.push(Od(m, g, h))), f) break;
						m = m.return;
					}
					0 < d.length && (c = new l(c, u, null, n, i), s.push({
						event: c,
						listeners: d
					}));
				}
			}
			if (!(t & 7)) {
				a: {
					if (c = e === "mouseover" || e === "pointerover", l = e === "mouseout" || e === "pointerout", c && n !== en && (u = n.relatedTarget || n.fromElement) && (ht(u) || u[ct])) break a;
					if ((l || c) && (c = i.window === i ? i : (c = i.ownerDocument) ? c.defaultView || c.parentWindow : window, l ? (u = n.relatedTarget || n.toElement, l = r, u = u ? ht(u) : null, u !== null && (f = o(u), d = u.tag, u !== f || d !== 5 && d !== 27 && d !== 6) && (u = null)) : (l = null, u = r), l !== u)) {
						if (d = On, g = "onMouseLeave", p = "onMouseEnter", m = "mouse", (e === "pointerout" || e === "pointerover") && (d = Bn, g = "onPointerLeave", p = "onPointerEnter", m = "pointer"), f = l == null ? c : _t(l), h = u == null ? c : _t(u), c = new d(g, m + "leave", l, n, i), c.target = f, c.relatedTarget = h, g = null, ht(i) === r && (d = new d(p, m + "enter", u, n, i), d.target = h, d.relatedTarget = f, g = d), f = g, l && u) b: {
							for (d = Ad, p = l, m = u, h = 0, g = p; g; g = d(g)) h++;
							g = 0;
							for (var _ = m; _; _ = d(_)) g++;
							for (; 0 < h - g;) p = d(p), h--;
							for (; 0 < g - h;) m = d(m), g--;
							for (; h--;) {
								if (p === m || m !== null && p === m.alternate) {
									d = p;
									break b;
								}
								p = d(p), m = d(m);
							}
							d = null;
						}
						else d = null;
						l !== null && jd(s, c, l, d, !1), u !== null && f !== null && jd(s, f, u, d, !0);
					}
				}
				a: {
					if (c = r ? _t(r) : window, l = c.nodeName && c.nodeName.toLowerCase(), l === "select" || l === "input" && c.type === "file") var v = ur;
					else if (ir(c)) if (dr) v = br;
					else {
						v = vr;
						var y = _r;
					}
					else l = c.nodeName, !l || l.toLowerCase() !== "input" || c.type !== "checkbox" && c.type !== "radio" ? r && Yt(r.elementType) && (v = ur) : v = yr;
					if (v &&= v(e, r)) {
						ar(s, v, n, i);
						break a;
					}
					y && y(e, c, r), e === "focusout" && r && c.type === "number" && r.memoizedProps.value != null && Vt(c, "number", c.value);
				}
				switch (y = r ? _t(r) : window, e) {
					case "focusin":
						(ir(y) || y.contentEditable === "true") && (Ar = y, jr = r, Mr = null);
						break;
					case "focusout":
						Mr = jr = Ar = null;
						break;
					case "mousedown":
						Nr = !0;
						break;
					case "contextmenu":
					case "mouseup":
					case "dragend":
						Nr = !1, Pr(s, n, i);
						break;
					case "selectionchange": if (kr) break;
					case "keydown":
					case "keyup": Pr(s, n, i);
				}
				var b;
				if (Kn) b: {
					switch (e) {
						case "compositionstart":
							var x = "onCompositionStart";
							break b;
						case "compositionend":
							x = "onCompositionEnd";
							break b;
						case "compositionupdate":
							x = "onCompositionUpdate";
							break b;
					}
					x = void 0;
				}
				else er ? Qn(e, n) && (x = "onCompositionEnd") : e === "keydown" && n.keyCode === 229 && (x = "onCompositionStart");
				x && (Yn && n.locale !== "ko" && (er || x !== "onCompositionStart" ? x === "onCompositionEnd" && er && (b = hn()) : (fn = i, pn = "value" in fn ? fn.value : fn.textContent, er = !0)), y = kd(r, x), 0 < y.length && (x = new Nn(x, e, null, n, i), s.push({
					event: x,
					listeners: y
				}), b ? x.data = b : (b = $n(n), b !== null && (x.data = b)))), (b = Jn ? tr(e, n) : nr(e, n)) && (x = kd(r, "onBeforeInput"), 0 < x.length && (y = new Nn("onBeforeInput", "beforeinput", null, n, i), s.push({
					event: y,
					listeners: x
				}), y.data = b)), vd(s, e, r, n, i);
			}
			J(s, t);
		});
	}
	function Od(e, t, n) {
		return {
			instance: e,
			listener: t,
			currentTarget: n
		};
	}
	function kd(e, t) {
		for (var n = t + "Capture", r = []; e !== null;) {
			var i = e, a = i.stateNode;
			if (i = i.tag, i !== 5 && i !== 26 && i !== 27 || a === null || (i = cn(e, n), i != null && r.unshift(Od(e, i, a)), i = cn(e, t), i != null && r.push(Od(e, i, a))), e.tag === 3) return r;
			e = e.return;
		}
		return [];
	}
	function Ad(e) {
		if (e === null) return null;
		do
			e = e.return;
		while (e && e.tag !== 5 && e.tag !== 27);
		return e || null;
	}
	function jd(e, t, n, r, i) {
		for (var a = t._reactName, o = []; n !== null && n !== r;) {
			var s = n, c = s.alternate, l = s.stateNode;
			if (s = s.tag, c !== null && c === r) break;
			s !== 5 && s !== 26 && s !== 27 || l === null || (c = l, i ? (l = cn(n, a), l != null && o.unshift(Od(n, l, c))) : i || (l = cn(n, a), l != null && o.push(Od(n, l, c)))), n = n.return;
		}
		o.length !== 0 && e.push({
			event: t,
			listeners: o
		});
	}
	var Md = /\r\n?/g, Nd = /\u0000|\uFFFD/g;
	function Pd(e) {
		return (typeof e == "string" ? e : "" + e).replace(Md, "\n").replace(Nd, "");
	}
	function Fd(e, t) {
		return t = Pd(t), Pd(e) === t;
	}
	function Id(e, t, n, r, a, o) {
		switch (n) {
			case "children":
				typeof r == "string" ? t === "body" || t === "textarea" && r === "" || Gt(e, r) : (typeof r == "number" || typeof r == "bigint") && t !== "body" && Gt(e, "" + r);
				break;
			case "className":
				kt(e, "class", r);
				break;
			case "tabIndex":
				kt(e, "tabindex", r);
				break;
			case "dir":
			case "role":
			case "viewBox":
			case "width":
			case "height":
				kt(e, n, r);
				break;
			case "style":
				Jt(e, r, o);
				break;
			case "data": if (t !== "object") {
				kt(e, "data", r);
				break;
			}
			case "src":
			case "href":
				if (r === "" && (t !== "a" || n !== "href")) {
					e.removeAttribute(n);
					break;
				}
				if (r == null || typeof r == "function" || typeof r == "symbol" || typeof r == "boolean") {
					e.removeAttribute(n);
					break;
				}
				r = Qt("" + r), e.setAttribute(n, r);
				break;
			case "action":
			case "formAction":
				if (typeof r == "function") {
					e.setAttribute(n, "javascript:throw new Error('A React form was unexpectedly submitted. If you called form.submit() manually, consider using form.requestSubmit() instead. If you\\'re trying to use event.stopPropagation() in a submit event handler, consider also calling event.preventDefault().')");
					break;
				} else typeof o == "function" && (n === "formAction" ? (t !== "input" && Id(e, t, "name", a.name, a, null), Id(e, t, "formEncType", a.formEncType, a, null), Id(e, t, "formMethod", a.formMethod, a, null), Id(e, t, "formTarget", a.formTarget, a, null)) : (Id(e, t, "encType", a.encType, a, null), Id(e, t, "method", a.method, a, null), Id(e, t, "target", a.target, a, null)));
				if (r == null || typeof r == "symbol" || typeof r == "boolean") {
					e.removeAttribute(n);
					break;
				}
				r = Qt("" + r), e.setAttribute(n, r);
				break;
			case "onClick":
				r != null && (e.onclick = $t);
				break;
			case "onScroll":
				r != null && Y("scroll", e);
				break;
			case "onScrollEnd":
				r != null && Y("scrollend", e);
				break;
			case "dangerouslySetInnerHTML":
				if (r != null) {
					if (typeof r != "object" || !("__html" in r)) throw Error(i(61));
					if (n = r.__html, n != null) {
						if (a.children != null) throw Error(i(60));
						e.innerHTML = n;
					}
				}
				break;
			case "multiple":
				e.multiple = r && typeof r != "function" && typeof r != "symbol";
				break;
			case "muted":
				e.muted = r && typeof r != "function" && typeof r != "symbol";
				break;
			case "suppressContentEditableWarning":
			case "suppressHydrationWarning":
			case "defaultValue":
			case "defaultChecked":
			case "innerHTML":
			case "ref": break;
			case "autoFocus": break;
			case "xlinkHref":
				if (r == null || typeof r == "function" || typeof r == "boolean" || typeof r == "symbol") {
					e.removeAttribute("xlink:href");
					break;
				}
				n = Qt("" + r), e.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href", n);
				break;
			case "contentEditable":
			case "spellCheck":
			case "draggable":
			case "value":
			case "autoReverse":
			case "externalResourcesRequired":
			case "focusable":
			case "preserveAlpha":
				r != null && typeof r != "function" && typeof r != "symbol" ? e.setAttribute(n, "" + r) : e.removeAttribute(n);
				break;
			case "inert":
			case "allowFullScreen":
			case "async":
			case "autoPlay":
			case "controls":
			case "default":
			case "defer":
			case "disabled":
			case "disablePictureInPicture":
			case "disableRemotePlayback":
			case "formNoValidate":
			case "hidden":
			case "loop":
			case "noModule":
			case "noValidate":
			case "open":
			case "playsInline":
			case "readOnly":
			case "required":
			case "reversed":
			case "scoped":
			case "seamless":
			case "itemScope":
				r && typeof r != "function" && typeof r != "symbol" ? e.setAttribute(n, "") : e.removeAttribute(n);
				break;
			case "capture":
			case "download":
				!0 === r ? e.setAttribute(n, "") : !1 !== r && r != null && typeof r != "function" && typeof r != "symbol" ? e.setAttribute(n, r) : e.removeAttribute(n);
				break;
			case "cols":
			case "rows":
			case "size":
			case "span":
				r != null && typeof r != "function" && typeof r != "symbol" && !isNaN(r) && 1 <= r ? e.setAttribute(n, r) : e.removeAttribute(n);
				break;
			case "rowSpan":
			case "start":
				r == null || typeof r == "function" || typeof r == "symbol" || isNaN(r) ? e.removeAttribute(n) : e.setAttribute(n, r);
				break;
			case "popover":
				Y("beforetoggle", e), Y("toggle", e), Ot(e, "popover", r);
				break;
			case "xlinkActuate":
				At(e, "http://www.w3.org/1999/xlink", "xlink:actuate", r);
				break;
			case "xlinkArcrole":
				At(e, "http://www.w3.org/1999/xlink", "xlink:arcrole", r);
				break;
			case "xlinkRole":
				At(e, "http://www.w3.org/1999/xlink", "xlink:role", r);
				break;
			case "xlinkShow":
				At(e, "http://www.w3.org/1999/xlink", "xlink:show", r);
				break;
			case "xlinkTitle":
				At(e, "http://www.w3.org/1999/xlink", "xlink:title", r);
				break;
			case "xlinkType":
				At(e, "http://www.w3.org/1999/xlink", "xlink:type", r);
				break;
			case "xmlBase":
				At(e, "http://www.w3.org/XML/1998/namespace", "xml:base", r);
				break;
			case "xmlLang":
				At(e, "http://www.w3.org/XML/1998/namespace", "xml:lang", r);
				break;
			case "xmlSpace":
				At(e, "http://www.w3.org/XML/1998/namespace", "xml:space", r);
				break;
			case "is":
				Ot(e, "is", r);
				break;
			case "innerText":
			case "textContent": break;
			default: (!(2 < n.length) || n[0] !== "o" && n[0] !== "O" || n[1] !== "n" && n[1] !== "N") && (n = Xt.get(n) || n, Ot(e, n, r));
		}
	}
	function Ld(e, t, n, r, a, o) {
		switch (n) {
			case "style":
				Jt(e, r, o);
				break;
			case "dangerouslySetInnerHTML":
				if (r != null) {
					if (typeof r != "object" || !("__html" in r)) throw Error(i(61));
					if (n = r.__html, n != null) {
						if (a.children != null) throw Error(i(60));
						e.innerHTML = n;
					}
				}
				break;
			case "children":
				typeof r == "string" ? Gt(e, r) : (typeof r == "number" || typeof r == "bigint") && Gt(e, "" + r);
				break;
			case "onScroll":
				r != null && Y("scroll", e);
				break;
			case "onScrollEnd":
				r != null && Y("scrollend", e);
				break;
			case "onClick":
				r != null && (e.onclick = $t);
				break;
			case "suppressContentEditableWarning":
			case "suppressHydrationWarning":
			case "innerHTML":
			case "ref": break;
			case "innerText":
			case "textContent": break;
			default: if (!xt.hasOwnProperty(n)) a: {
				if (n[0] === "o" && n[1] === "n" && (a = n.endsWith("Capture"), t = n.slice(2, a ? n.length - 7 : void 0), o = e[st] || null, o = o == null ? null : o[n], typeof o == "function" && e.removeEventListener(t, o, a), typeof r == "function")) {
					typeof o != "function" && o !== null && (n in e ? e[n] = null : e.hasAttribute(n) && e.removeAttribute(n)), e.addEventListener(t, r, a);
					break a;
				}
				n in e ? e[n] = r : !0 === r ? e.setAttribute(n, "") : Ot(e, n, r);
			}
		}
	}
	function Rd(e, t, n) {
		switch (t) {
			case "div":
			case "span":
			case "svg":
			case "path":
			case "a":
			case "g":
			case "p":
			case "li": break;
			case "img":
				Y("error", e), Y("load", e);
				var r = !1, a = !1, o;
				for (o in n) if (n.hasOwnProperty(o)) {
					var s = n[o];
					if (s != null) switch (o) {
						case "src":
							r = !0;
							break;
						case "srcSet":
							a = !0;
							break;
						case "children":
						case "dangerouslySetInnerHTML": throw Error(i(137, t));
						default: Id(e, t, o, s, n, null);
					}
				}
				a && Id(e, t, "srcSet", n.srcSet, n, null), r && Id(e, t, "src", n.src, n, null);
				return;
			case "input":
				Y("invalid", e);
				var c = o = s = a = null, l = null, u = null;
				for (r in n) if (n.hasOwnProperty(r)) {
					var d = n[r];
					if (d != null) switch (r) {
						case "name":
							a = d;
							break;
						case "type":
							s = d;
							break;
						case "checked":
							l = d;
							break;
						case "defaultChecked":
							u = d;
							break;
						case "value":
							o = d;
							break;
						case "defaultValue":
							c = d;
							break;
						case "children":
						case "dangerouslySetInnerHTML":
							if (d != null) throw Error(i(137, t));
							break;
						default: Id(e, t, r, d, n, null);
					}
				}
				Bt(e, o, c, l, u, s, a, !1);
				return;
			case "select":
				for (a in Y("invalid", e), r = s = o = null, n) if (n.hasOwnProperty(a) && (c = n[a], c != null)) switch (a) {
					case "value":
						o = c;
						break;
					case "defaultValue":
						s = c;
						break;
					case "multiple": r = c;
					default: Id(e, t, a, c, n, null);
				}
				t = o, n = s, e.multiple = !!r, t == null ? n != null && Ht(e, !!r, n, !0) : Ht(e, !!r, t, !1);
				return;
			case "textarea":
				for (s in Y("invalid", e), o = a = r = null, n) if (n.hasOwnProperty(s) && (c = n[s], c != null)) switch (s) {
					case "value":
						r = c;
						break;
					case "defaultValue":
						a = c;
						break;
					case "children":
						o = c;
						break;
					case "dangerouslySetInnerHTML":
						if (c != null) throw Error(i(91));
						break;
					default: Id(e, t, s, c, n, null);
				}
				Wt(e, r, a, o);
				return;
			case "option":
				for (l in n) if (n.hasOwnProperty(l) && (r = n[l], r != null)) switch (l) {
					case "selected":
						e.selected = r && typeof r != "function" && typeof r != "symbol";
						break;
					default: Id(e, t, l, r, n, null);
				}
				return;
			case "dialog":
				Y("beforetoggle", e), Y("toggle", e), Y("cancel", e), Y("close", e);
				break;
			case "iframe":
			case "object":
				Y("load", e);
				break;
			case "video":
			case "audio":
				for (r = 0; r < xd.length; r++) Y(xd[r], e);
				break;
			case "image":
				Y("error", e), Y("load", e);
				break;
			case "details":
				Y("toggle", e);
				break;
			case "embed":
			case "source":
			case "link": Y("error", e), Y("load", e);
			case "area":
			case "base":
			case "br":
			case "col":
			case "hr":
			case "keygen":
			case "meta":
			case "param":
			case "track":
			case "wbr":
			case "menuitem":
				for (u in n) if (n.hasOwnProperty(u) && (r = n[u], r != null)) switch (u) {
					case "children":
					case "dangerouslySetInnerHTML": throw Error(i(137, t));
					default: Id(e, t, u, r, n, null);
				}
				return;
			default: if (Yt(t)) {
				for (d in n) n.hasOwnProperty(d) && (r = n[d], r !== void 0 && Ld(e, t, d, r, n, void 0));
				return;
			}
		}
		for (c in n) n.hasOwnProperty(c) && (r = n[c], r != null && Id(e, t, c, r, n, null));
	}
	function zd(e, t, n, r) {
		switch (t) {
			case "div":
			case "span":
			case "svg":
			case "path":
			case "a":
			case "g":
			case "p":
			case "li": break;
			case "input":
				var a = null, o = null, s = null, c = null, l = null, u = null, d = null;
				for (m in n) {
					var f = n[m];
					if (n.hasOwnProperty(m) && f != null) switch (m) {
						case "checked": break;
						case "value": break;
						case "defaultValue": l = f;
						default: r.hasOwnProperty(m) || Id(e, t, m, null, r, f);
					}
				}
				for (var p in r) {
					var m = r[p];
					if (f = n[p], r.hasOwnProperty(p) && (m != null || f != null)) switch (p) {
						case "type":
							o = m;
							break;
						case "name":
							a = m;
							break;
						case "checked":
							u = m;
							break;
						case "defaultChecked":
							d = m;
							break;
						case "value":
							s = m;
							break;
						case "defaultValue":
							c = m;
							break;
						case "children":
						case "dangerouslySetInnerHTML":
							if (m != null) throw Error(i(137, t));
							break;
						default: m !== f && Id(e, t, p, m, r, f);
					}
				}
				zt(e, s, c, l, u, d, o, a);
				return;
			case "select":
				for (o in m = s = c = p = null, n) if (l = n[o], n.hasOwnProperty(o) && l != null) switch (o) {
					case "value": break;
					case "multiple": m = l;
					default: r.hasOwnProperty(o) || Id(e, t, o, null, r, l);
				}
				for (a in r) if (o = r[a], l = n[a], r.hasOwnProperty(a) && (o != null || l != null)) switch (a) {
					case "value":
						p = o;
						break;
					case "defaultValue":
						c = o;
						break;
					case "multiple": s = o;
					default: o !== l && Id(e, t, a, o, r, l);
				}
				t = c, n = s, r = m, p == null ? !!r != !!n && (t == null ? Ht(e, !!n, n ? [] : "", !1) : Ht(e, !!n, t, !0)) : Ht(e, !!n, p, !1);
				return;
			case "textarea":
				for (c in m = p = null, n) if (a = n[c], n.hasOwnProperty(c) && a != null && !r.hasOwnProperty(c)) switch (c) {
					case "value": break;
					case "children": break;
					default: Id(e, t, c, null, r, a);
				}
				for (s in r) if (a = r[s], o = n[s], r.hasOwnProperty(s) && (a != null || o != null)) switch (s) {
					case "value":
						p = a;
						break;
					case "defaultValue":
						m = a;
						break;
					case "children": break;
					case "dangerouslySetInnerHTML":
						if (a != null) throw Error(i(91));
						break;
					default: a !== o && Id(e, t, s, a, r, o);
				}
				Ut(e, p, m);
				return;
			case "option":
				for (var h in n) if (p = n[h], n.hasOwnProperty(h) && p != null && !r.hasOwnProperty(h)) switch (h) {
					case "selected":
						e.selected = !1;
						break;
					default: Id(e, t, h, null, r, p);
				}
				for (l in r) if (p = r[l], m = n[l], r.hasOwnProperty(l) && p !== m && (p != null || m != null)) switch (l) {
					case "selected":
						e.selected = p && typeof p != "function" && typeof p != "symbol";
						break;
					default: Id(e, t, l, p, r, m);
				}
				return;
			case "img":
			case "link":
			case "area":
			case "base":
			case "br":
			case "col":
			case "embed":
			case "hr":
			case "keygen":
			case "meta":
			case "param":
			case "source":
			case "track":
			case "wbr":
			case "menuitem":
				for (var g in n) p = n[g], n.hasOwnProperty(g) && p != null && !r.hasOwnProperty(g) && Id(e, t, g, null, r, p);
				for (u in r) if (p = r[u], m = n[u], r.hasOwnProperty(u) && p !== m && (p != null || m != null)) switch (u) {
					case "children":
					case "dangerouslySetInnerHTML":
						if (p != null) throw Error(i(137, t));
						break;
					default: Id(e, t, u, p, r, m);
				}
				return;
			default: if (Yt(t)) {
				for (var _ in n) p = n[_], n.hasOwnProperty(_) && p !== void 0 && !r.hasOwnProperty(_) && Ld(e, t, _, void 0, r, p);
				for (d in r) p = r[d], m = n[d], !r.hasOwnProperty(d) || p === m || p === void 0 && m === void 0 || Ld(e, t, d, p, r, m);
				return;
			}
		}
		for (var v in n) p = n[v], n.hasOwnProperty(v) && p != null && !r.hasOwnProperty(v) && Id(e, t, v, null, r, p);
		for (f in r) p = r[f], m = n[f], !r.hasOwnProperty(f) || p === m || p == null && m == null || Id(e, t, f, p, r, m);
	}
	function Bd(e) {
		switch (e) {
			case "css":
			case "script":
			case "font":
			case "img":
			case "image":
			case "input":
			case "link": return !0;
			default: return !1;
		}
	}
	function Vd() {
		if (typeof performance.getEntriesByType == "function") {
			for (var e = 0, t = 0, n = performance.getEntriesByType("resource"), r = 0; r < n.length; r++) {
				var i = n[r], a = i.transferSize, o = i.initiatorType, s = i.duration;
				if (a && s && Bd(o)) {
					for (o = 0, s = i.responseEnd, r += 1; r < n.length; r++) {
						var c = n[r], l = c.startTime;
						if (l > s) break;
						var u = c.transferSize, d = c.initiatorType;
						u && Bd(d) && (c = c.responseEnd, o += u * (c < s ? 1 : (s - l) / (c - l)));
					}
					if (--r, t += 8 * (a + o) / (i.duration / 1e3), e++, 10 < e) break;
				}
			}
			if (0 < e) return t / e / 1e6;
		}
		return navigator.connection && (e = navigator.connection.downlink, typeof e == "number") ? e : 5;
	}
	var Hd = null, Ud = null;
	function Wd(e) {
		return e.nodeType === 9 ? e : e.ownerDocument;
	}
	function Gd(e) {
		switch (e) {
			case "http://www.w3.org/2000/svg": return 1;
			case "http://www.w3.org/1998/Math/MathML": return 2;
			default: return 0;
		}
	}
	function Kd(e, t) {
		if (e === 0) switch (t) {
			case "svg": return 1;
			case "math": return 2;
			default: return 0;
		}
		return e === 1 && t === "foreignObject" ? 0 : e;
	}
	function qd(e, t) {
		return e === "textarea" || e === "noscript" || typeof t.children == "string" || typeof t.children == "number" || typeof t.children == "bigint" || typeof t.dangerouslySetInnerHTML == "object" && t.dangerouslySetInnerHTML !== null && t.dangerouslySetInnerHTML.__html != null;
	}
	var Jd = null;
	function Yd() {
		var e = window.event;
		return e && e.type === "popstate" ? e === Jd ? !1 : (Jd = e, !0) : (Jd = null, !1);
	}
	var Xd = typeof setTimeout == "function" ? setTimeout : void 0, Zd = typeof clearTimeout == "function" ? clearTimeout : void 0, Qd = typeof Promise == "function" ? Promise : void 0, $d = typeof queueMicrotask == "function" ? queueMicrotask : Qd === void 0 ? Xd : function(e) {
		return Qd.resolve(null).then(e).catch(ef);
	};
	function ef(e) {
		setTimeout(function() {
			throw e;
		});
	}
	function tf(e) {
		return e === "head";
	}
	function nf(e, t) {
		var n = t, r = 0;
		do {
			var i = n.nextSibling;
			if (e.removeChild(n), i && i.nodeType === 8) if (n = i.data, n === "/$" || n === "/&") {
				if (r === 0) {
					e.removeChild(i), Lp(t);
					return;
				}
				r--;
			} else if (n === "$" || n === "$?" || n === "$~" || n === "$!" || n === "&") r++;
			else if (n === "html") _f(e.ownerDocument.documentElement);
			else if (n === "head") {
				n = e.ownerDocument.head, _f(n);
				for (var a = n.firstChild; a;) {
					var o = a.nextSibling, s = a.nodeName;
					a[pt] || s === "SCRIPT" || s === "STYLE" || s === "LINK" && a.rel.toLowerCase() === "stylesheet" || n.removeChild(a), a = o;
				}
			} else n === "body" && _f(e.ownerDocument.body);
			n = i;
		} while (n);
		Lp(t);
	}
	function rf(e, t) {
		var n = e;
		e = 0;
		do {
			var r = n.nextSibling;
			if (n.nodeType === 1 ? t ? (n._stashedDisplay = n.style.display, n.style.display = "none") : (n.style.display = n._stashedDisplay || "", n.getAttribute("style") === "" && n.removeAttribute("style")) : n.nodeType === 3 && (t ? (n._stashedText = n.nodeValue, n.nodeValue = "") : n.nodeValue = n._stashedText || ""), r && r.nodeType === 8) if (n = r.data, n === "/$") {
				if (e === 0) break;
				e--;
			} else n !== "$" && n !== "$?" && n !== "$~" && n !== "$!" || e++;
			n = r;
		} while (n);
	}
	function af(e) {
		var t = e.firstChild;
		for (t && t.nodeType === 10 && (t = t.nextSibling); t;) {
			var n = t;
			switch (t = t.nextSibling, n.nodeName) {
				case "HTML":
				case "HEAD":
				case "BODY":
					af(n), mt(n);
					continue;
				case "SCRIPT":
				case "STYLE": continue;
				case "LINK": if (n.rel.toLowerCase() === "stylesheet") continue;
			}
			e.removeChild(n);
		}
	}
	function of(e, t, n, r) {
		for (; e.nodeType === 1;) {
			var i = n;
			if (e.nodeName.toLowerCase() !== t.toLowerCase()) {
				if (!r && (e.nodeName !== "INPUT" || e.type !== "hidden")) break;
			} else if (!r) if (t === "input" && e.type === "hidden") {
				var a = i.name == null ? null : "" + i.name;
				if (i.type === "hidden" && e.getAttribute("name") === a) return e;
			} else return e;
			else if (!e[pt]) switch (t) {
				case "meta":
					if (!e.hasAttribute("itemprop")) break;
					return e;
				case "link":
					if (a = e.getAttribute("rel"), a === "stylesheet" && e.hasAttribute("data-precedence") || a !== i.rel || e.getAttribute("href") !== (i.href == null || i.href === "" ? null : i.href) || e.getAttribute("crossorigin") !== (i.crossOrigin == null ? null : i.crossOrigin) || e.getAttribute("title") !== (i.title == null ? null : i.title)) break;
					return e;
				case "style":
					if (e.hasAttribute("data-precedence")) break;
					return e;
				case "script":
					if (a = e.getAttribute("src"), (a !== (i.src == null ? null : i.src) || e.getAttribute("type") !== (i.type == null ? null : i.type) || e.getAttribute("crossorigin") !== (i.crossOrigin == null ? null : i.crossOrigin)) && a && e.hasAttribute("async") && !e.hasAttribute("itemprop")) break;
					return e;
				default: return e;
			}
			if (e = ff(e.nextSibling), e === null) break;
		}
		return null;
	}
	function sf(e, t, n) {
		if (t === "") return null;
		for (; e.nodeType !== 3;) if ((e.nodeType !== 1 || e.nodeName !== "INPUT" || e.type !== "hidden") && !n || (e = ff(e.nextSibling), e === null)) return null;
		return e;
	}
	function cf(e, t) {
		for (; e.nodeType !== 8;) if ((e.nodeType !== 1 || e.nodeName !== "INPUT" || e.type !== "hidden") && !t || (e = ff(e.nextSibling), e === null)) return null;
		return e;
	}
	function lf(e) {
		return e.data === "$?" || e.data === "$~";
	}
	function uf(e) {
		return e.data === "$!" || e.data === "$?" && e.ownerDocument.readyState !== "loading";
	}
	function df(e, t) {
		var n = e.ownerDocument;
		if (e.data === "$~") e._reactRetry = t;
		else if (e.data !== "$?" || n.readyState !== "loading") t();
		else {
			var r = function() {
				t(), n.removeEventListener("DOMContentLoaded", r);
			};
			n.addEventListener("DOMContentLoaded", r), e._reactRetry = r;
		}
	}
	function ff(e) {
		for (; e != null; e = e.nextSibling) {
			var t = e.nodeType;
			if (t === 1 || t === 3) break;
			if (t === 8) {
				if (t = e.data, t === "$" || t === "$!" || t === "$?" || t === "$~" || t === "&" || t === "F!" || t === "F") break;
				if (t === "/$" || t === "/&") return null;
			}
		}
		return e;
	}
	var pf = null;
	function mf(e) {
		e = e.nextSibling;
		for (var t = 0; e;) {
			if (e.nodeType === 8) {
				var n = e.data;
				if (n === "/$" || n === "/&") {
					if (t === 0) return ff(e.nextSibling);
					t--;
				} else n !== "$" && n !== "$!" && n !== "$?" && n !== "$~" && n !== "&" || t++;
			}
			e = e.nextSibling;
		}
		return null;
	}
	function hf(e) {
		e = e.previousSibling;
		for (var t = 0; e;) {
			if (e.nodeType === 8) {
				var n = e.data;
				if (n === "$" || n === "$!" || n === "$?" || n === "$~" || n === "&") {
					if (t === 0) return e;
					t--;
				} else n !== "/$" && n !== "/&" || t++;
			}
			e = e.previousSibling;
		}
		return null;
	}
	function gf(e, t, n) {
		switch (t = Wd(n), e) {
			case "html":
				if (e = t.documentElement, !e) throw Error(i(452));
				return e;
			case "head":
				if (e = t.head, !e) throw Error(i(453));
				return e;
			case "body":
				if (e = t.body, !e) throw Error(i(454));
				return e;
			default: throw Error(i(451));
		}
	}
	function _f(e) {
		for (var t = e.attributes; t.length;) e.removeAttributeNode(t[0]);
		mt(e);
	}
	var vf = /* @__PURE__ */ new Map(), yf = /* @__PURE__ */ new Set();
	function bf(e) {
		return typeof e.getRootNode == "function" ? e.getRootNode() : e.nodeType === 9 ? e : e.ownerDocument;
	}
	var xf = N.d;
	N.d = {
		f: Sf,
		r: Cf,
		D: Ef,
		C: Df,
		L: Of,
		m: kf,
		X: jf,
		S: Af,
		M: Mf
	};
	function Sf() {
		var e = xf.f(), t = Cu();
		return e || t;
	}
	function Cf(e) {
		var t = gt(e);
		t !== null && t.tag === 5 && t.type === "form" ? ws(t) : xf.r(e);
	}
	var wf = typeof document > "u" ? null : document;
	function Tf(e, t, n) {
		var r = wf;
		if (r && typeof t == "string" && t) {
			var i = Rt(t);
			i = "link[rel=\"" + e + "\"][href=\"" + i + "\"]", typeof n == "string" && (i += "[crossorigin=\"" + n + "\"]"), yf.has(i) || (yf.add(i), e = {
				rel: e,
				crossOrigin: n,
				href: t
			}, r.querySelector(i) === null && (t = r.createElement("link"), Rd(t, "link", e), yt(t), r.head.appendChild(t)));
		}
	}
	function Ef(e) {
		xf.D(e), Tf("dns-prefetch", e, null);
	}
	function Df(e, t) {
		xf.C(e, t), Tf("preconnect", e, t);
	}
	function Of(e, t, n) {
		xf.L(e, t, n);
		var r = wf;
		if (r && e && t) {
			var i = "link[rel=\"preload\"][as=\"" + Rt(t) + "\"]";
			t === "image" && n && n.imageSrcSet ? (i += "[imagesrcset=\"" + Rt(n.imageSrcSet) + "\"]", typeof n.imageSizes == "string" && (i += "[imagesizes=\"" + Rt(n.imageSizes) + "\"]")) : i += "[href=\"" + Rt(e) + "\"]";
			var a = i;
			switch (t) {
				case "style":
					a = Pf(e);
					break;
				case "script": a = Rf(e);
			}
			vf.has(a) || (e = f({
				rel: "preload",
				href: t === "image" && n && n.imageSrcSet ? void 0 : e,
				as: t
			}, n), vf.set(a, e), r.querySelector(i) !== null || t === "style" && r.querySelector(Ff(a)) || t === "script" && r.querySelector(zf(a)) || (t = r.createElement("link"), Rd(t, "link", e), yt(t), r.head.appendChild(t)));
		}
	}
	function kf(e, t) {
		xf.m(e, t);
		var n = wf;
		if (n && e) {
			var r = t && typeof t.as == "string" ? t.as : "script", i = "link[rel=\"modulepreload\"][as=\"" + Rt(r) + "\"][href=\"" + Rt(e) + "\"]", a = i;
			switch (r) {
				case "audioworklet":
				case "paintworklet":
				case "serviceworker":
				case "sharedworker":
				case "worker":
				case "script": a = Rf(e);
			}
			if (!vf.has(a) && (e = f({
				rel: "modulepreload",
				href: e
			}, t), vf.set(a, e), n.querySelector(i) === null)) {
				switch (r) {
					case "audioworklet":
					case "paintworklet":
					case "serviceworker":
					case "sharedworker":
					case "worker":
					case "script": if (n.querySelector(zf(a))) return;
				}
				r = n.createElement("link"), Rd(r, "link", e), yt(r), n.head.appendChild(r);
			}
		}
	}
	function Af(e, t, n) {
		xf.S(e, t, n);
		var r = wf;
		if (r && e) {
			var i = vt(r).hoistableStyles, a = Pf(e);
			t ||= "default";
			var o = i.get(a);
			if (!o) {
				var s = {
					loading: 0,
					preload: null
				};
				if (o = r.querySelector(Ff(a))) s.loading = 5;
				else {
					e = f({
						rel: "stylesheet",
						href: e,
						"data-precedence": t
					}, n), (n = vf.get(a)) && Hf(e, n);
					var c = o = r.createElement("link");
					yt(c), Rd(c, "link", e), c._p = new Promise(function(e, t) {
						c.onload = e, c.onerror = t;
					}), c.addEventListener("load", function() {
						s.loading |= 1;
					}), c.addEventListener("error", function() {
						s.loading |= 2;
					}), s.loading |= 4, Vf(o, t, r);
				}
				o = {
					type: "stylesheet",
					instance: o,
					count: 1,
					state: s
				}, i.set(a, o);
			}
		}
	}
	function jf(e, t) {
		xf.X(e, t);
		var n = wf;
		if (n && e) {
			var r = vt(n).hoistableScripts, i = Rf(e), a = r.get(i);
			a || (a = n.querySelector(zf(i)), a || (e = f({
				src: e,
				async: !0
			}, t), (t = vf.get(i)) && Uf(e, t), a = n.createElement("script"), yt(a), Rd(a, "link", e), n.head.appendChild(a)), a = {
				type: "script",
				instance: a,
				count: 1,
				state: null
			}, r.set(i, a));
		}
	}
	function Mf(e, t) {
		xf.M(e, t);
		var n = wf;
		if (n && e) {
			var r = vt(n).hoistableScripts, i = Rf(e), a = r.get(i);
			a || (a = n.querySelector(zf(i)), a || (e = f({
				src: e,
				async: !0,
				type: "module"
			}, t), (t = vf.get(i)) && Uf(e, t), a = n.createElement("script"), yt(a), Rd(a, "link", e), n.head.appendChild(a)), a = {
				type: "script",
				instance: a,
				count: 1,
				state: null
			}, r.set(i, a));
		}
	}
	function Nf(e, t, n, r) {
		var a = (a = se.current) ? bf(a) : null;
		if (!a) throw Error(i(446));
		switch (e) {
			case "meta":
			case "title": return null;
			case "style": return typeof n.precedence == "string" && typeof n.href == "string" ? (t = Pf(n.href), n = vt(a).hoistableStyles, r = n.get(t), r || (r = {
				type: "style",
				instance: null,
				count: 0,
				state: null
			}, n.set(t, r)), r) : {
				type: "void",
				instance: null,
				count: 0,
				state: null
			};
			case "link":
				if (n.rel === "stylesheet" && typeof n.href == "string" && typeof n.precedence == "string") {
					e = Pf(n.href);
					var o = vt(a).hoistableStyles, s = o.get(e);
					if (s || (a = a.ownerDocument || a, s = {
						type: "stylesheet",
						instance: null,
						count: 0,
						state: {
							loading: 0,
							preload: null
						}
					}, o.set(e, s), (o = a.querySelector(Ff(e))) && !o._p && (s.instance = o, s.state.loading = 5), vf.has(e) || (n = {
						rel: "preload",
						as: "style",
						href: n.href,
						crossOrigin: n.crossOrigin,
						integrity: n.integrity,
						media: n.media,
						hrefLang: n.hrefLang,
						referrerPolicy: n.referrerPolicy
					}, vf.set(e, n), o || Lf(a, e, n, s.state))), t && r === null) throw Error(i(528, ""));
					return s;
				}
				if (t && r !== null) throw Error(i(529, ""));
				return null;
			case "script": return t = n.async, n = n.src, typeof n == "string" && t && typeof t != "function" && typeof t != "symbol" ? (t = Rf(n), n = vt(a).hoistableScripts, r = n.get(t), r || (r = {
				type: "script",
				instance: null,
				count: 0,
				state: null
			}, n.set(t, r)), r) : {
				type: "void",
				instance: null,
				count: 0,
				state: null
			};
			default: throw Error(i(444, e));
		}
	}
	function Pf(e) {
		return "href=\"" + Rt(e) + "\"";
	}
	function Ff(e) {
		return "link[rel=\"stylesheet\"][" + e + "]";
	}
	function If(e) {
		return f({}, e, {
			"data-precedence": e.precedence,
			precedence: null
		});
	}
	function Lf(e, t, n, r) {
		e.querySelector("link[rel=\"preload\"][as=\"style\"][" + t + "]") ? r.loading = 1 : (t = e.createElement("link"), r.preload = t, t.addEventListener("load", function() {
			return r.loading |= 1;
		}), t.addEventListener("error", function() {
			return r.loading |= 2;
		}), Rd(t, "link", n), yt(t), e.head.appendChild(t));
	}
	function Rf(e) {
		return "[src=\"" + Rt(e) + "\"]";
	}
	function zf(e) {
		return "script[async]" + e;
	}
	function Bf(e, t, n) {
		if (t.count++, t.instance === null) switch (t.type) {
			case "style":
				var r = e.querySelector("style[data-href~=\"" + Rt(n.href) + "\"]");
				if (r) return t.instance = r, yt(r), r;
				var a = f({}, n, {
					"data-href": n.href,
					"data-precedence": n.precedence,
					href: null,
					precedence: null
				});
				return r = (e.ownerDocument || e).createElement("style"), yt(r), Rd(r, "style", a), Vf(r, n.precedence, e), t.instance = r;
			case "stylesheet":
				a = Pf(n.href);
				var o = e.querySelector(Ff(a));
				if (o) return t.state.loading |= 4, t.instance = o, yt(o), o;
				r = If(n), (a = vf.get(a)) && Hf(r, a), o = (e.ownerDocument || e).createElement("link"), yt(o);
				var s = o;
				return s._p = new Promise(function(e, t) {
					s.onload = e, s.onerror = t;
				}), Rd(o, "link", r), t.state.loading |= 4, Vf(o, n.precedence, e), t.instance = o;
			case "script": return o = Rf(n.src), (a = e.querySelector(zf(o))) ? (t.instance = a, yt(a), a) : (r = n, (a = vf.get(o)) && (r = f({}, n), Uf(r, a)), e = e.ownerDocument || e, a = e.createElement("script"), yt(a), Rd(a, "link", r), e.head.appendChild(a), t.instance = a);
			case "void": return null;
			default: throw Error(i(443, t.type));
		}
		else t.type === "stylesheet" && !(t.state.loading & 4) && (r = t.instance, t.state.loading |= 4, Vf(r, n.precedence, e));
		return t.instance;
	}
	function Vf(e, t, n) {
		for (var r = n.querySelectorAll("link[rel=\"stylesheet\"][data-precedence],style[data-precedence]"), i = r.length ? r[r.length - 1] : null, a = i, o = 0; o < r.length; o++) {
			var s = r[o];
			if (s.dataset.precedence === t) a = s;
			else if (a !== i) break;
		}
		a ? a.parentNode.insertBefore(e, a.nextSibling) : (t = n.nodeType === 9 ? n.head : n, t.insertBefore(e, t.firstChild));
	}
	function Hf(e, t) {
		e.crossOrigin ??= t.crossOrigin, e.referrerPolicy ??= t.referrerPolicy, e.title ??= t.title;
	}
	function Uf(e, t) {
		e.crossOrigin ??= t.crossOrigin, e.referrerPolicy ??= t.referrerPolicy, e.integrity ??= t.integrity;
	}
	var Wf = null;
	function Gf(e, t, n) {
		if (Wf === null) {
			var r = /* @__PURE__ */ new Map(), i = Wf = /* @__PURE__ */ new Map();
			i.set(n, r);
		} else i = Wf, r = i.get(n), r || (r = /* @__PURE__ */ new Map(), i.set(n, r));
		if (r.has(e)) return r;
		for (r.set(e, null), n = n.getElementsByTagName(e), i = 0; i < n.length; i++) {
			var a = n[i];
			if (!(a[pt] || a[ot] || e === "link" && a.getAttribute("rel") === "stylesheet") && a.namespaceURI !== "http://www.w3.org/2000/svg") {
				var o = a.getAttribute(t) || "";
				o = e + o;
				var s = r.get(o);
				s ? s.push(a) : r.set(o, [a]);
			}
		}
		return r;
	}
	function Kf(e, t, n) {
		e = e.ownerDocument || e, e.head.insertBefore(n, t === "title" ? e.querySelector("head > title") : null);
	}
	function qf(e, t, n) {
		if (n === 1 || t.itemProp != null) return !1;
		switch (e) {
			case "meta":
			case "title": return !0;
			case "style":
				if (typeof t.precedence != "string" || typeof t.href != "string" || t.href === "") break;
				return !0;
			case "link":
				if (typeof t.rel != "string" || typeof t.href != "string" || t.href === "" || t.onLoad || t.onError) break;
				switch (t.rel) {
					case "stylesheet": return e = t.disabled, typeof t.precedence == "string" && e == null;
					default: return !0;
				}
			case "script": if (t.async && typeof t.async != "function" && typeof t.async != "symbol" && !t.onLoad && !t.onError && t.src && typeof t.src == "string") return !0;
		}
		return !1;
	}
	function Jf(e) {
		return !(e.type === "stylesheet" && !(e.state.loading & 3));
	}
	function Yf(e, t, n, r) {
		if (n.type === "stylesheet" && (typeof r.media != "string" || !1 !== matchMedia(r.media).matches) && !(n.state.loading & 4)) {
			if (n.instance === null) {
				var i = Pf(r.href), a = t.querySelector(Ff(i));
				if (a) {
					t = a._p, typeof t == "object" && t && typeof t.then == "function" && (e.count++, e = Qf.bind(e), t.then(e, e)), n.state.loading |= 4, n.instance = a, yt(a);
					return;
				}
				a = t.ownerDocument || t, r = If(r), (i = vf.get(i)) && Hf(r, i), a = a.createElement("link"), yt(a);
				var o = a;
				o._p = new Promise(function(e, t) {
					o.onload = e, o.onerror = t;
				}), Rd(a, "link", r), n.instance = a;
			}
			e.stylesheets === null && (e.stylesheets = /* @__PURE__ */ new Map()), e.stylesheets.set(n, t), (t = n.state.preload) && !(n.state.loading & 3) && (e.count++, n = Qf.bind(e), t.addEventListener("load", n), t.addEventListener("error", n));
		}
	}
	var Xf = 0;
	function Zf(e, t) {
		return e.stylesheets && e.count === 0 && ep(e, e.stylesheets), 0 < e.count || 0 < e.imgCount ? function(n) {
			var r = setTimeout(function() {
				if (e.stylesheets && ep(e, e.stylesheets), e.unsuspend) {
					var t = e.unsuspend;
					e.unsuspend = null, t();
				}
			}, 6e4 + t);
			0 < e.imgBytes && Xf === 0 && (Xf = 62500 * Vd());
			var i = setTimeout(function() {
				if (e.waitingForImages = !1, e.count === 0 && (e.stylesheets && ep(e, e.stylesheets), e.unsuspend)) {
					var t = e.unsuspend;
					e.unsuspend = null, t();
				}
			}, (e.imgBytes > Xf ? 50 : 800) + t);
			return e.unsuspend = n, function() {
				e.unsuspend = null, clearTimeout(r), clearTimeout(i);
			};
		} : null;
	}
	function Qf() {
		if (this.count--, this.count === 0 && (this.imgCount === 0 || !this.waitingForImages)) {
			if (this.stylesheets) ep(this, this.stylesheets);
			else if (this.unsuspend) {
				var e = this.unsuspend;
				this.unsuspend = null, e();
			}
		}
	}
	var $f = null;
	function ep(e, t) {
		e.stylesheets = null, e.unsuspend !== null && (e.count++, $f = /* @__PURE__ */ new Map(), t.forEach(tp, e), $f = null, Qf.call(e));
	}
	function tp(e, t) {
		if (!(t.state.loading & 4)) {
			var n = $f.get(e);
			if (n) var r = n.get(null);
			else {
				n = /* @__PURE__ */ new Map(), $f.set(e, n);
				for (var i = e.querySelectorAll("link[data-precedence],style[data-precedence]"), a = 0; a < i.length; a++) {
					var o = i[a];
					(o.nodeName === "LINK" || o.getAttribute("media") !== "not all") && (n.set(o.dataset.precedence, o), r = o);
				}
				r && n.set(null, r);
			}
			i = t.instance, o = i.getAttribute("data-precedence"), a = n.get(o) || r, a === r && n.set(null, i), n.set(o, i), this.count++, r = Qf.bind(this), i.addEventListener("load", r), i.addEventListener("error", r), a ? a.parentNode.insertBefore(i, a.nextSibling) : (e = e.nodeType === 9 ? e.head : e, e.insertBefore(i, e.firstChild)), t.state.loading |= 4;
		}
	}
	var np = {
		$$typeof: b,
		Provider: null,
		Consumer: null,
		_currentValue: P,
		_currentValue2: P,
		_threadCount: 0
	};
	function rp(e, t, n, r, i, a, o, s, c) {
		this.tag = 1, this.containerInfo = e, this.pingCache = this.current = this.pendingChildren = null, this.timeoutHandle = -1, this.callbackNode = this.next = this.pendingContext = this.context = this.cancelPendingCommit = null, this.callbackPriority = 0, this.expirationTimes = Xe(-1), this.entangledLanes = this.shellSuspendCounter = this.errorRecoveryDisabledLanes = this.expiredLanes = this.warmLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0, this.entanglements = Xe(0), this.hiddenUpdates = Xe(null), this.identifierPrefix = r, this.onUncaughtError = i, this.onCaughtError = a, this.onRecoverableError = o, this.pooledCache = null, this.pooledCacheLanes = 0, this.formState = c, this.incompleteTransitions = /* @__PURE__ */ new Map();
	}
	function ip(e, t, n, r, i, a, o, s, c, l, u, d) {
		return e = new rp(e, t, n, o, c, l, u, d, s), t = 1, !0 === a && (t |= 24), a = ci(3, null, null, t), e.current = a, a.stateNode = e, t = ca(), t.refCount++, e.pooledCache = t, t.refCount++, a.memoizedState = {
			element: r,
			isDehydrated: n,
			cache: t
		}, za(a), e;
	}
	function ap(e) {
		return e ? (e = oi, e) : oi;
	}
	function op(e, t, n, r, i, a) {
		i = ap(i), r.context === null ? r.context = i : r.pendingContext = i, r = Va(t), r.payload = { element: n }, a = a === void 0 ? null : a, a !== null && (r.callback = a), n = Ha(e, r, t), n !== null && (vu(n, e, t), Ua(n, e, t));
	}
	function sp(e, t) {
		if (e = e.memoizedState, e !== null && e.dehydrated !== null) {
			var n = e.retryLane;
			e.retryLane = n !== 0 && n < t ? n : t;
		}
	}
	function cp(e, t) {
		sp(e, t), (e = e.alternate) && sp(e, t);
	}
	function lp(e) {
		if (e.tag === 13 || e.tag === 31) {
			var t = ri(e, 67108864);
			t !== null && vu(t, e, 67108864), cp(e, 67108864);
		}
	}
	function up(e) {
		if (e.tag === 13 || e.tag === 31) {
			var t = gu();
			t = nt(t);
			var n = ri(e, t);
			n !== null && vu(n, e, t), cp(e, t);
		}
	}
	var dp = !0;
	function fp(e, t, n, r) {
		var i = M.T;
		M.T = null;
		var a = N.p;
		try {
			N.p = 2, mp(e, t, n, r);
		} finally {
			N.p = a, M.T = i;
		}
	}
	function pp(e, t, n, r) {
		var i = M.T;
		M.T = null;
		var a = N.p;
		try {
			N.p = 8, mp(e, t, n, r);
		} finally {
			N.p = a, M.T = i;
		}
	}
	function mp(e, t, n, r) {
		if (dp) {
			var i = hp(r);
			if (i === null) Dd(e, t, r, gp, n), Dp(e, r);
			else if (kp(i, e, t, n, r)) r.stopPropagation();
			else if (Dp(e, r), t & 4 && -1 < Ep.indexOf(e)) {
				for (; i !== null;) {
					var a = gt(i);
					if (a !== null) switch (a.tag) {
						case 3:
							if (a = a.stateNode, a.current.memoizedState.isDehydrated) {
								var o = Ge(a.pendingLanes);
								if (o !== 0) {
									var s = a;
									for (s.pendingLanes |= 2, s.entangledLanes |= 2; o;) {
										var c = 1 << 31 - Re(o);
										s.entanglements[1] |= c, o &= ~c;
									}
									sd(a), !(zl & 6) && (iu = Ee() + 500, cd(0, !1));
								}
							}
							break;
						case 31:
						case 13: s = ri(a, 2), s !== null && vu(s, a, 2), Cu(), cp(a, 2);
					}
					if (a = hp(r), a === null && Dd(e, t, r, gp, n), a === i) break;
					i = a;
				}
				i !== null && r.stopPropagation();
			} else Dd(e, t, r, null, n);
		}
	}
	function hp(e) {
		return e = tn(e), _p(e);
	}
	var gp = null;
	function _p(e) {
		if (gp = null, e = ht(e), e !== null) {
			var t = o(e);
			if (t === null) e = null;
			else {
				var n = t.tag;
				if (n === 13) {
					if (e = s(t), e !== null) return e;
					e = null;
				} else if (n === 31) {
					if (e = c(t), e !== null) return e;
					e = null;
				} else if (n === 3) {
					if (t.stateNode.current.memoizedState.isDehydrated) return t.tag === 3 ? t.stateNode.containerInfo : null;
					e = null;
				} else t !== e && (e = null);
			}
		}
		return gp = e, null;
	}
	function vp(e) {
		switch (e) {
			case "beforetoggle":
			case "cancel":
			case "click":
			case "close":
			case "contextmenu":
			case "copy":
			case "cut":
			case "auxclick":
			case "dblclick":
			case "dragend":
			case "dragstart":
			case "drop":
			case "focusin":
			case "focusout":
			case "input":
			case "invalid":
			case "keydown":
			case "keypress":
			case "keyup":
			case "mousedown":
			case "mouseup":
			case "paste":
			case "pause":
			case "play":
			case "pointercancel":
			case "pointerdown":
			case "pointerup":
			case "ratechange":
			case "reset":
			case "resize":
			case "seeked":
			case "submit":
			case "toggle":
			case "touchcancel":
			case "touchend":
			case "touchstart":
			case "volumechange":
			case "change":
			case "selectionchange":
			case "textInput":
			case "compositionstart":
			case "compositionend":
			case "compositionupdate":
			case "beforeblur":
			case "afterblur":
			case "beforeinput":
			case "blur":
			case "fullscreenchange":
			case "focus":
			case "hashchange":
			case "popstate":
			case "select":
			case "selectstart": return 2;
			case "drag":
			case "dragenter":
			case "dragexit":
			case "dragleave":
			case "dragover":
			case "mousemove":
			case "mouseout":
			case "mouseover":
			case "pointermove":
			case "pointerout":
			case "pointerover":
			case "scroll":
			case "touchmove":
			case "wheel":
			case "mouseenter":
			case "mouseleave":
			case "pointerenter":
			case "pointerleave": return 8;
			case "message": switch (De()) {
				case Oe: return 2;
				case ke: return 8;
				case Ae:
				case je: return 32;
				case Me: return 268435456;
				default: return 32;
			}
			default: return 32;
		}
	}
	var yp = !1, bp = null, xp = null, Sp = null, Cp = /* @__PURE__ */ new Map(), wp = /* @__PURE__ */ new Map(), Tp = [], Ep = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset".split(" ");
	function Dp(e, t) {
		switch (e) {
			case "focusin":
			case "focusout":
				bp = null;
				break;
			case "dragenter":
			case "dragleave":
				xp = null;
				break;
			case "mouseover":
			case "mouseout":
				Sp = null;
				break;
			case "pointerover":
			case "pointerout":
				Cp.delete(t.pointerId);
				break;
			case "gotpointercapture":
			case "lostpointercapture": wp.delete(t.pointerId);
		}
	}
	function Op(e, t, n, r, i, a) {
		return e === null || e.nativeEvent !== a ? (e = {
			blockedOn: t,
			domEventName: n,
			eventSystemFlags: r,
			nativeEvent: a,
			targetContainers: [i]
		}, t !== null && (t = gt(t), t !== null && lp(t)), e) : (e.eventSystemFlags |= r, t = e.targetContainers, i !== null && t.indexOf(i) === -1 && t.push(i), e);
	}
	function kp(e, t, n, r, i) {
		switch (t) {
			case "focusin": return bp = Op(bp, e, t, n, r, i), !0;
			case "dragenter": return xp = Op(xp, e, t, n, r, i), !0;
			case "mouseover": return Sp = Op(Sp, e, t, n, r, i), !0;
			case "pointerover":
				var a = i.pointerId;
				return Cp.set(a, Op(Cp.get(a) || null, e, t, n, r, i)), !0;
			case "gotpointercapture": return a = i.pointerId, wp.set(a, Op(wp.get(a) || null, e, t, n, r, i)), !0;
		}
		return !1;
	}
	function Ap(e) {
		var t = ht(e.target);
		if (t !== null) {
			var n = o(t);
			if (n !== null) {
				if (t = n.tag, t === 13) {
					if (t = s(n), t !== null) {
						e.blockedOn = t, it(e.priority, function() {
							up(n);
						});
						return;
					}
				} else if (t === 31) {
					if (t = c(n), t !== null) {
						e.blockedOn = t, it(e.priority, function() {
							up(n);
						});
						return;
					}
				} else if (t === 3 && n.stateNode.current.memoizedState.isDehydrated) {
					e.blockedOn = n.tag === 3 ? n.stateNode.containerInfo : null;
					return;
				}
			}
		}
		e.blockedOn = null;
	}
	function jp(e) {
		if (e.blockedOn !== null) return !1;
		for (var t = e.targetContainers; 0 < t.length;) {
			var n = hp(e.nativeEvent);
			if (n === null) {
				n = e.nativeEvent;
				var r = new n.constructor(n.type, n);
				en = r, n.target.dispatchEvent(r), en = null;
			} else return t = gt(n), t !== null && lp(t), e.blockedOn = n, !1;
			t.shift();
		}
		return !0;
	}
	function Mp(e, t, n) {
		jp(e) && n.delete(t);
	}
	function Np() {
		yp = !1, bp !== null && jp(bp) && (bp = null), xp !== null && jp(xp) && (xp = null), Sp !== null && jp(Sp) && (Sp = null), Cp.forEach(Mp), wp.forEach(Mp);
	}
	function Pp(e, n) {
		e.blockedOn === n && (e.blockedOn = null, yp || (yp = !0, t.unstable_scheduleCallback(t.unstable_NormalPriority, Np)));
	}
	var Fp = null;
	function Ip(e) {
		Fp !== e && (Fp = e, t.unstable_scheduleCallback(t.unstable_NormalPriority, function() {
			Fp === e && (Fp = null);
			for (var t = 0; t < e.length; t += 3) {
				var n = e[t], r = e[t + 1], i = e[t + 2];
				if (typeof r != "function") {
					if (_p(r || n) === null) continue;
					break;
				}
				var a = gt(n);
				a !== null && (e.splice(t, 3), t -= 3, Ss(a, {
					pending: !0,
					data: i,
					method: n.method,
					action: r
				}, r, i));
			}
		}));
	}
	function Lp(e) {
		function t(t) {
			return Pp(t, e);
		}
		bp !== null && Pp(bp, e), xp !== null && Pp(xp, e), Sp !== null && Pp(Sp, e), Cp.forEach(t), wp.forEach(t);
		for (var n = 0; n < Tp.length; n++) {
			var r = Tp[n];
			r.blockedOn === e && (r.blockedOn = null);
		}
		for (; 0 < Tp.length && (n = Tp[0], n.blockedOn === null);) Ap(n), n.blockedOn === null && Tp.shift();
		if (n = (e.ownerDocument || e).$$reactFormReplay, n != null) for (r = 0; r < n.length; r += 3) {
			var i = n[r], a = n[r + 1], o = i[st] || null;
			if (typeof a == "function") o || Ip(n);
			else if (o) {
				var s = null;
				if (a && a.hasAttribute("formAction")) {
					if (i = a, o = a[st] || null) s = o.formAction;
					else if (_p(i) !== null) continue;
				} else s = o.action;
				typeof s == "function" ? n[r + 1] = s : (n.splice(r, 3), r -= 3), Ip(n);
			}
		}
	}
	function Rp() {
		function e(e) {
			e.canIntercept && e.info === "react-transition" && e.intercept({
				handler: function() {
					return new Promise(function(e) {
						return i = e;
					});
				},
				focusReset: "manual",
				scroll: "manual"
			});
		}
		function t() {
			i !== null && (i(), i = null), r || setTimeout(n, 20);
		}
		function n() {
			if (!r && !navigation.transition) {
				var e = navigation.currentEntry;
				e && e.url != null && navigation.navigate(e.url, {
					state: e.getState(),
					info: "react-transition",
					history: "replace"
				});
			}
		}
		if (typeof navigation == "object") {
			var r = !1, i = null;
			return navigation.addEventListener("navigate", e), navigation.addEventListener("navigatesuccess", t), navigation.addEventListener("navigateerror", t), setTimeout(n, 100), function() {
				r = !0, navigation.removeEventListener("navigate", e), navigation.removeEventListener("navigatesuccess", t), navigation.removeEventListener("navigateerror", t), i !== null && (i(), i = null);
			};
		}
	}
	function zp(e) {
		this._internalRoot = e;
	}
	Bp.prototype.render = zp.prototype.render = function(e) {
		var t = this._internalRoot;
		if (t === null) throw Error(i(409));
		var n = t.current;
		op(n, gu(), e, t, null, null);
	}, Bp.prototype.unmount = zp.prototype.unmount = function() {
		var e = this._internalRoot;
		if (e !== null) {
			this._internalRoot = null;
			var t = e.containerInfo;
			op(e.current, 2, null, e, null, null), Cu(), t[ct] = null;
		}
	};
	function Bp(e) {
		this._internalRoot = e;
	}
	Bp.prototype.unstable_scheduleHydration = function(e) {
		if (e) {
			var t = R();
			e = {
				blockedOn: null,
				target: e,
				priority: t
			};
			for (var n = 0; n < Tp.length && t !== 0 && t < Tp[n].priority; n++);
			Tp.splice(n, 0, e), n === 0 && Ap(e);
		}
	};
	var Vp = n.version;
	if (Vp !== "19.2.7") throw Error(i(527, Vp, "19.2.7"));
	N.findDOMNode = function(e) {
		var t = e._reactInternals;
		if (t === void 0) throw typeof e.render == "function" ? Error(i(188)) : (e = Object.keys(e).join(","), Error(i(268, e)));
		return e = u(t), e = e === null ? null : d(e), e = e === null ? null : e.stateNode, e;
	};
	var Hp = {
		bundleType: 0,
		version: "19.2.7",
		rendererPackageName: "react-dom",
		currentDispatcherRef: M,
		reconcilerVersion: "19.2.7"
	};
	if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
		var Up = __REACT_DEVTOOLS_GLOBAL_HOOK__;
		if (!Up.isDisabled && Up.supportsFiber) try {
			Fe = Up.inject(Hp), Ie = Up;
		} catch {}
	}
	e.createRoot = function(e, t) {
		if (!a(e)) throw Error(i(299));
		var n = !1, r = "", o = Gs, s = Ks, c = qs;
		return t != null && (!0 === t.unstable_strictMode && (n = !0), t.identifierPrefix !== void 0 && (r = t.identifierPrefix), t.onUncaughtError !== void 0 && (o = t.onUncaughtError), t.onCaughtError !== void 0 && (s = t.onCaughtError), t.onRecoverableError !== void 0 && (c = t.onRecoverableError)), t = ip(e, 1, !1, null, null, n, r, null, o, s, c, Rp), e[ct] = t.current, Td(e), new zp(t);
	};
})), he = /* @__PURE__ */ n(((e, t) => {
	function n() {
		if (!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function")) try {
			__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(n);
		} catch (e) {
			console.error(e);
		}
	}
	n(), t.exports = me();
})), I = le(), ge = he();
function _e() {
	return {
		async: !1,
		breaks: !1,
		extensions: null,
		gfm: !0,
		hooks: null,
		pedantic: !1,
		renderer: null,
		silent: !1,
		tokenizer: null,
		walkTokens: null
	};
}
var ve = _e();
function ye(e) {
	ve = e;
}
var be = { exec: () => null };
function xe(e) {
	let t = [];
	return (n) => {
		let r = Math.max(0, Math.min(3, n - 1)), i = t[r];
		return i || (i = e(r), t[r] = i), i;
	};
}
function L(e, t = "") {
	let n = typeof e == "string" ? e : e.source, r = {
		replace: (e, t) => {
			let i = typeof t == "string" ? t : t.source;
			return i = i.replace(Ce.caret, "$1"), n = n.replace(e, i), r;
		},
		getRegex: () => new RegExp(n, t)
	};
	return r;
}
var Se = ((e = "") => {
	try {
		return !!RegExp("(?<=1)(?<!1)" + e);
	} catch {
		return !1;
	}
})(), Ce = {
	codeRemoveIndent: /^(?: {1,4}| {0,3}\t)/gm,
	outputLinkReplace: /\\([\[\]])/g,
	indentCodeCompensation: /^(\s+)(?:```)/,
	beginningSpace: /^\s+/,
	endingHash: /#$/,
	startingSpaceChar: /^ /,
	endingSpaceChar: / $/,
	nonSpaceChar: /[^ ]/,
	newLineCharGlobal: /\n/g,
	tabCharGlobal: /\t/g,
	multipleSpaceGlobal: /\s+/g,
	blankLine: /^[ \t]*$/,
	doubleBlankLine: /\n[ \t]*\n[ \t]*$/,
	blockquoteStart: /^ {0,3}>/,
	blockquoteSetextReplace: /\n {0,3}((?:=+|-+) *)(?=\n|$)/g,
	blockquoteSetextReplace2: /^ {0,3}>[ \t]?/gm,
	listReplaceNesting: /^ {1,4}(?=( {4})*[^ ])/g,
	listIsTask: /^\[[ xX]\] +\S/,
	listReplaceTask: /^\[[ xX]\] +/,
	listTaskCheckbox: /\[[ xX]\]/,
	anyLine: /\n.*\n/,
	hrefBrackets: /^<(.*)>$/,
	tableDelimiter: /[:|]/,
	tableAlignChars: /^\||\| *$/g,
	tableRowBlankLine: /\n[ \t]*$/,
	tableAlignRight: /^ *-+: *$/,
	tableAlignCenter: /^ *:-+: *$/,
	tableAlignLeft: /^ *:-+ *$/,
	startATag: /^<a /i,
	endATag: /^<\/a>/i,
	startPreScriptTag: /^<(pre|code|kbd|script)(\s|>)/i,
	endPreScriptTag: /^<\/(pre|code|kbd|script)(\s|>)/i,
	startAngleBracket: /^</,
	endAngleBracket: />$/,
	pedanticHrefTitle: /^([^'"]*[^\s])\s+(['"])(.*)\2/,
	unicodeAlphaNumeric: /[\p{L}\p{N}]/u,
	escapeTest: /[&<>"']/,
	escapeReplace: /[&<>"']/g,
	escapeTestNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/,
	escapeReplaceNoEncode: /[<>"']|&(?!(#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g,
	caret: /(^|[^\[])\^/g,
	percentDecode: /%25/g,
	findPipe: /\|/g,
	splitPipe: / \|/,
	slashPipe: /\\\|/g,
	carriageReturn: /\r\n|\r/g,
	spaceLine: /^ +$/gm,
	notSpaceStart: /^\S*/,
	endingNewline: /\n$/,
	listItemRegex: (e) => RegExp(`^( {0,3}${e})((?:[	 ][^\\n]*)?(?:\\n|$))`),
	nextBulletRegex: xe((e) => RegExp(`^ {0,${e}}(?:[*+-]|\\d{1,9}[.)])((?:[ 	][^\\n]*)?(?:\\n|$))`)),
	hrRegex: xe((e) => RegExp(`^ {0,${e}}((?:- *){3,}|(?:_ *){3,}|(?:\\* *){3,})(?:\\n+|$)`)),
	fencesBeginRegex: xe((e) => RegExp(`^ {0,${e}}(?:\`\`\`|~~~)`)),
	headingBeginRegex: xe((e) => RegExp(`^ {0,${e}}#`)),
	htmlBeginRegex: xe((e) => RegExp(`^ {0,${e}}<(?:[a-z].*>|!--)`, "i")),
	blockquoteBeginRegex: xe((e) => RegExp(`^ {0,${e}}>`))
}, we = /^(?:[ \t]*(?:\n|$))+/, Te = /^((?: {4}| {0,3}\t)[^\n]+(?:\n(?:[ \t]*(?:\n|$))*)?)+/, Ee = /^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)/, De = /^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)/, Oe = /^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)/, ke = / {0,3}(?:[*+-]|\d{1,9}[.)])/, Ae = /^(?!bull |blockCode|fences|blockquote|heading|html|table)((?:.|\n(?!\s*?\n|bull |blockCode|fences|blockquote|heading|html|table))+?)\n {0,3}(=+|-+) *(?:\n+|$)/, je = L(Ae).replace(/bull/g, ke).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/\|table/g, "").getRegex(), Me = L(Ae).replace(/bull/g, ke).replace(/blockCode/g, /(?: {4}| {0,3}\t)/).replace(/fences/g, / {0,3}(?:`{3,}|~{3,})/).replace(/blockquote/g, / {0,3}>/).replace(/heading/g, / {0,3}#{1,6}(?:\s|$)/).replace(/html/g, / {0,3}<[^\n>]+>\n/).replace(/table/g, / {0,3}\|?(?:[:\- ]*\|)+[\:\- ]*\n/).getRegex(), Ne = /^([^\n]+(?:\n(?!hr|heading|lheading|blockquote|fences|list|html|table|[ \t]+\n)[^\n]+)*)/, Pe = /^[^\n]+/, Fe = /(?!\s*\])(?:\\[\s\S]|[^\[\]\\])+/, Ie = L(/^ {0,3}\[(label)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(title))? *(?:\n+|$)/).replace("label", Fe).replace("title", /(?:"(?:\\"?|[^"\\])*"|'[^'\n]*(?:\n[^'\n]+)*\n?'|\([^()]*\))/).getRegex(), Le = L(/^(bull)([ \t][^\n]*?)?(?:\n|$)/).replace(/bull/g, ke).getRegex(), Re = "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul", ze = /<!--(?:-?>|[\s\S]*?(?:-->|$))/, Be = L("^ {0,3}(?:<(script|pre|style|textarea)[\\s>][\\s\\S]*?(?:</\\1>[^\\n]*\\n*|$)|comment[^\\n]*(\\n+|$)|<\\?[\\s\\S]*?(?:\\?>[^\\n]*\\n*|$)|<![A-Z][\\s\\S]*?(?:>[^\\n]*\\n*|$)|<!\\[CDATA\\[[\\s\\S]*?(?:\\]\\]>[^\\n]*\\n*|$)|</?(tag)(?: +|\\n|/?>)[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|<(?!script|pre|style|textarea)([a-z][\\w-]*)(?:attribute)*? */?>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$)|</(?!script|pre|style|textarea)[a-z][\\w-]*\\s*>(?=[ \\t]*(?:\\n|$))[\\s\\S]*?(?:(?:\\n[ 	]*)+\\n|$))", "i").replace("comment", ze).replace("tag", Re).replace("attribute", / +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *'[^'\n]*'| *= *[^\s"'=<>`]+)?/).getRegex(), Ve = (e) => L(Ne).replace("hr", De).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("|table", "").replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~~~)[^\\n]*\\n").replace("list", e).replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Re).getRegex(), He = Ve(/ {0,3}(?:[*+-]|1[.)])[ \t]+[^ \t\n]/), Ue = Ve(/ {0,3}(?:[*+-]|\d{1,9}[.)])(?:[ \t]|\n|$)/), We = {
	blockquote: L(/^( {0,3}> ?(paragraph|[^\n]*)(?:\n|$))+/).replace("paragraph", Ue).getRegex(),
	code: Te,
	def: Ie,
	fences: Ee,
	heading: Oe,
	hr: De,
	html: Be,
	lheading: je,
	list: Le,
	newline: we,
	paragraph: He,
	table: be,
	text: Pe
}, Ge = L("^ *([^\\n ].*)\\n {0,3}((?:\\| *)?:?-+:? *(?:\\| *:?-+:? *)*(?:\\| *)?)(?:\\n((?:(?! *\\n|hr|heading|blockquote|code|fences|list|html).*(?:\\n|$))*)\\n*|$)").replace("hr", De).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("blockquote", " {0,3}>").replace("code", "(?: {4}| {0,3}	)[^\\n]").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~~~)[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Re).getRegex(), Ke = {
	...We,
	lheading: Me,
	table: Ge,
	paragraph: L(Ne).replace("hr", De).replace("heading", " {0,3}#{1,6}(?:\\s|$)").replace("|lheading", "").replace("table", Ge).replace("blockquote", " {0,3}>").replace("fences", " {0,3}(?:`{3,}(?=[^`\\n]*\\n)|~~~)[^\\n]*\\n").replace("list", " {0,3}(?:[*+-]|1[.)])[ \\t]+[^ \\t\\n]").replace("html", "</?(?:tag)(?: +|\\n|/?>)|<(?:script|pre|style|textarea|!--)").replace("tag", Re).getRegex()
}, qe = {
	...We,
	html: L("^ *(?:comment *(?:\\n|\\s*$)|<(tag)[\\s\\S]+?</\\1> *(?:\\n{2,}|\\s*$)|<tag(?:\"[^\"]*\"|'[^']*'|\\s[^'\"/>\\s]*)*?/?> *(?:\\n{2,}|\\s*$))").replace("comment", ze).replace(/tag/g, "(?!(?:a|em|strong|small|s|cite|q|dfn|abbr|data|time|code|var|samp|kbd|sub|sup|i|b|u|mark|ruby|rt|rp|bdi|bdo|span|br|wbr|ins|del|img)\\b)\\w+(?!:|[^\\w\\s@]*@)\\b").getRegex(),
	def: /^ *\[([^\]]+)\]: *<?([^\s>]+)>?(?: +(["(][^\n]+[")]))? *(?:\n+|$)/,
	heading: /^(#{1,6})(.*)(?:\n+|$)/,
	fences: be,
	lheading: /^(.+?)\n {0,3}(=+|-+) *(?:\n+|$)/,
	paragraph: L(Ne).replace("hr", De).replace("heading", " *#{1,6} *[^\n]").replace("lheading", je).replace("|table", "").replace("blockquote", " {0,3}>").replace("|fences", "").replace("|list", "").replace("|html", "").replace("|tag", "").getRegex()
}, Je = /^\\([!"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])/, Ye = /^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)/, Xe = /^( {2,}|\\)\n(?!\s*$)/, Ze = /^(`+|[^`])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\<!\[`*_]|\b_|$)|[^ ](?= {2,}\n)))/, Qe = /[\p{P}\p{S}]/u, $e = /[\s\p{P}\p{S}]/u, et = /[^\s\p{P}\p{S}]/u, tt = L(/^((?![*_])punctSpace)/, "u").replace(/punctSpace/g, $e).getRegex(), nt = /(?!~)[\p{P}\p{S}]/u, rt = /(?!~)[\s\p{P}\p{S}]/u, R = /(?:[^\s\p{P}\p{S}]|~)/u, it = L(/link|precode-code|html/, "g").replace("link", /\[(?:[^\[\]`]|(?<a>`+)[^`]+\k<a>(?!`))*?\]\((?:\\[\s\S]|[^\\\(\)]|\((?:\\[\s\S]|[^\\\(\)])*\))*\)/).replace("precode-", Se ? "(?<!`)()" : "(^^|[^`])").replace("code", /(?<b>`+)[^`]+\k<b>(?!`)/).replace("html", /<(?! )[^<>]*?>/).getRegex(), at = /^(?:\*+(?:((?!\*)punct)|([^\s*]))?)|^_+(?:((?!_)punct)|([^\s_]))?/, ot = L(at, "u").replace(/punct/g, Qe).getRegex(), st = L(at, "u").replace(/punct/g, nt).getRegex(), ct = "^[^_*]*?__[^_*]*?\\*[^_*]*?(?=__)|[^*]+(?=[^*])|(?!\\*)punct(\\*+)(?=[\\s]|$)|notPunctSpace(\\*+)(?!\\*)(?=punctSpace|$)|(?!\\*)punctSpace(\\*+)(?=notPunctSpace)|[\\s](\\*+)(?!\\*)(?=punct)|(?!\\*)punct(\\*+)(?!\\*)(?=punct)|notPunctSpace(\\*+)(?=notPunctSpace)", lt = L(ct, "gu").replace(/notPunctSpace/g, et).replace(/punctSpace/g, $e).replace(/punct/g, Qe).getRegex(), ut = L(ct, "gu").replace(/notPunctSpace/g, R).replace(/punctSpace/g, rt).replace(/punct/g, nt).getRegex(), dt = L("^[^_*]*?\\*\\*[^_*]*?_[^_*]*?(?=\\*\\*)|[^_]+(?=[^_])|(?!_)punct(_+)(?=[\\s]|$)|notPunctSpace(_+)(?!_)(?=punctSpace|$)|(?!_)punctSpace(_+)(?=notPunctSpace)|[\\s](_+)(?!_)(?=punct)|(?!_)punct(_+)(?!_)(?=punct)", "gu").replace(/notPunctSpace/g, et).replace(/punctSpace/g, $e).replace(/punct/g, Qe).getRegex(), ft = L(/^~~?(?:((?!~)punct)|[^\s~])/, "u").replace(/punct/g, Qe).getRegex(), pt = L("^[^~]+(?=[^~])|(?!~)punct(~~?)(?=[\\s]|$)|notPunctSpace(~~?)(?!~)(?=punctSpace|$)|(?!~)punctSpace(~~?)(?=notPunctSpace)|[\\s](~~?)(?!~)(?=punct)|(?!~)punct(~~?)(?!~)(?=punct)|notPunctSpace(~~?)(?=notPunctSpace)", "gu").replace(/notPunctSpace/g, et).replace(/punctSpace/g, $e).replace(/punct/g, Qe).getRegex(), mt = L(/\\(punct)/, "gu").replace(/punct/g, Qe).getRegex(), ht = L(/^<(scheme:[^\s\x00-\x1f<>]*|email)>/).replace("scheme", /[a-zA-Z][a-zA-Z0-9+.-]{1,31}/).replace("email", /[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+(@)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+(?![-_])/).getRegex(), gt = L(ze).replace("(?:-->|$)", "-->").getRegex(), _t = L("^comment|^</[a-zA-Z][\\w:-]*\\s*>|^<[a-zA-Z][\\w-]*(?:attribute)*?\\s*/?>|^<\\?[\\s\\S]*?\\?>|^<![a-zA-Z]+\\s[\\s\\S]*?>|^<!\\[CDATA\\[[\\s\\S]*?\\]\\]>").replace("comment", gt).replace("attribute", /\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*'[^']*'|\s*=\s*[^\s"'=<>`]+)?/).getRegex(), vt = /(?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?/, yt = L(/^!?\[(label)\]\(\s*(href)(?:(?:[ \t]+(?:\n[ \t]*)?|\n[ \t]*)(title))?\s*\)/).replace("label", vt).replace("href", /<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]+|(?=\))/).replace("title", /"(?:\\"?|[^"\\])*"|'(?:\\'?|[^'\\])*'|\((?:\\\)?|[^)\\])*\)/).getRegex(), bt = L(/^!?\[(label)\]\[(ref)\]/).replace("label", vt).replace("ref", Fe).getRegex(), xt = L(/^!?\[(ref)\](?:\[\])?/).replace("ref", Fe).getRegex(), St = L("reflink|nolink(?!\\()", "g").replace("reflink", bt).replace("nolink", xt).getRegex(), Ct = /[hH][tT][tT][pP][sS]?|[fF][tT][pP]/, wt = {
	_backpedal: be,
	anyPunctuation: mt,
	autolink: ht,
	blockSkip: it,
	br: Xe,
	code: Ye,
	del: be,
	delLDelim: be,
	delRDelim: be,
	emStrongLDelim: ot,
	emStrongRDelimAst: lt,
	emStrongRDelimUnd: dt,
	escape: Je,
	link: yt,
	nolink: xt,
	punctuation: tt,
	reflink: bt,
	reflinkSearch: St,
	tag: _t,
	text: Ze,
	url: be
}, Tt = {
	...wt,
	link: L(/^!?\[(label)\]\((.*?)\)/).replace("label", vt).getRegex(),
	reflink: L(/^!?\[(label)\]\s*\[([^\]]*)\]/).replace("label", vt).getRegex()
}, Et = {
	...wt,
	emStrongRDelimAst: ut,
	emStrongLDelim: st,
	delLDelim: ft,
	delRDelim: pt,
	url: L(/^((?:protocol):\/\/|www\.)(?:[a-zA-Z0-9\-]+\.?)+[^\s<]*|^email/).replace("protocol", Ct).replace("email", /[A-Za-z0-9._+-]+(@)[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])/).getRegex(),
	_backpedal: /(?:[^?!.,:;*_'"~()&]+|\([^)]*\)|&(?![a-zA-Z0-9]+;$)|[?!.,:;*_'"~)]+(?!$))+/,
	del: /^(~~?)(?=[^\s~])((?:\\[\s\S]|[^\\])*?(?:\\[\s\S]|[^\s~\\]))\1(?=[^~]|$)/,
	text: L(/^(`+|~+|[^`~])(?:(?=[`~])|(?= {2,}\n)|(?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)|[\s\S]*?(?:(?=[\\<!\[`*~_]|\b_|protocol:\/\/|www\.|$)|[^ ](?= {2,}\n)|[^a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-](?=[a-zA-Z0-9.!#$%&'*+\/=?_`{\|}~-]+@)))/).replace("protocol", Ct).getRegex()
}, Dt = {
	...Et,
	br: L(Xe).replace("{2,}", "*").getRegex(),
	text: L(Et.text).replace("\\b_", "\\b_| {2,}\\n").replace(/\{2,\}/g, "*").getRegex()
}, Ot = {
	normal: We,
	gfm: Ke,
	pedantic: qe
}, kt = {
	normal: wt,
	gfm: Et,
	breaks: Dt,
	pedantic: Tt
}, At = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	"\"": "&quot;",
	"'": "&#39;"
}, jt = (e) => At[e];
function Mt(e, t) {
	if (t) {
		if (Ce.escapeTest.test(e)) return e.replace(Ce.escapeReplace, jt);
	} else if (Ce.escapeTestNoEncode.test(e)) return e.replace(Ce.escapeReplaceNoEncode, jt);
	return e;
}
function Nt(e) {
	try {
		e = encodeURI(e).replace(Ce.percentDecode, "%");
	} catch {
		return null;
	}
	return e;
}
function Pt(e, t) {
	let n = e.replace(Ce.findPipe, (e, t, n) => {
		let r = !1, i = t;
		for (; --i >= 0 && n[i] === "\\";) r = !r;
		return r ? "|" : " |";
	}).split(Ce.splitPipe), r = 0;
	if (n[0].trim() || n.shift(), n.length > 0 && !n.at(-1)?.trim() && n.pop(), t) if (n.length > t) n.splice(t);
	else for (; n.length < t;) n.push("");
	for (; r < n.length; r++) n[r] = n[r].trim().replace(Ce.slashPipe, "|");
	return n;
}
function Ft(e, t, n) {
	let r = e.length;
	if (r === 0) return "";
	let i = 0;
	for (; i < r;) {
		let a = e.charAt(r - i - 1);
		if (a === t && !n) i++;
		else if (a !== t && n) i++;
		else break;
	}
	return e.slice(0, r - i);
}
function It(e) {
	let t = e.split("\n"), n = t.length - 1;
	for (; n >= 0 && Ce.blankLine.test(t[n]);) n--;
	return t.length - n <= 2 ? e : t.slice(0, n + 1).join("\n");
}
function Lt(e, t) {
	if (e.indexOf(t[1]) === -1) return -1;
	let n = 0;
	for (let r = 0; r < e.length; r++) if (e[r] === "\\") r++;
	else if (e[r] === t[0]) n++;
	else if (e[r] === t[1] && (n--, n < 0)) return r;
	return n > 0 ? -2 : -1;
}
function Rt(e, t = 0) {
	let n = t, r = "";
	for (let t of e) if (t === "	") {
		let e = 4 - n % 4;
		r += " ".repeat(e), n += e;
	} else r += t, n++;
	return r;
}
function zt(e, t, n, r, i) {
	let a = t.href, o = t.title || null, s = e[1].replace(i.other.outputLinkReplace, "$1");
	r.state.inLink = !0;
	let c = {
		type: e[0].charAt(0) === "!" ? "image" : "link",
		raw: n,
		href: a,
		title: o,
		text: s,
		tokens: r.inlineTokens(s)
	};
	return r.state.inLink = !1, c;
}
function Bt(e, t, n) {
	let r = e.match(n.other.indentCodeCompensation);
	if (r === null) return t;
	let i = r[1];
	return t.split("\n").map((e) => {
		let t = e.match(n.other.beginningSpace);
		if (t === null) return e;
		let [r] = t;
		return r.length >= i.length ? e.slice(i.length) : e;
	}).join("\n");
}
var Vt = class {
	options;
	rules;
	lexer;
	constructor(e) {
		this.options = e || ve;
	}
	space(e) {
		let t = this.rules.block.newline.exec(e);
		if (t && t[0].length > 0) return {
			type: "space",
			raw: t[0]
		};
	}
	code(e) {
		let t = this.rules.block.code.exec(e);
		if (t) {
			let e = this.options.pedantic ? t[0] : It(t[0]);
			return {
				type: "code",
				raw: e,
				codeBlockStyle: "indented",
				text: e.replace(this.rules.other.codeRemoveIndent, "")
			};
		}
	}
	fences(e) {
		let t = this.rules.block.fences.exec(e);
		if (t) {
			let e = t[0], n = Bt(e, t[3] || "", this.rules);
			return {
				type: "code",
				raw: e,
				lang: t[2] ? t[2].trim().replace(this.rules.inline.anyPunctuation, "$1") : t[2],
				text: n
			};
		}
	}
	heading(e) {
		let t = this.rules.block.heading.exec(e);
		if (t) {
			let e = t[2].trim();
			if (this.rules.other.endingHash.test(e)) {
				let t = Ft(e, "#");
				(this.options.pedantic || !t || this.rules.other.endingSpaceChar.test(t)) && (e = t.trim());
			}
			return {
				type: "heading",
				raw: Ft(t[0], "\n"),
				depth: t[1].length,
				text: e,
				tokens: this.lexer.inline(e)
			};
		}
	}
	hr(e) {
		let t = this.rules.block.hr.exec(e);
		if (t) return {
			type: "hr",
			raw: Ft(t[0], "\n")
		};
	}
	blockquote(e) {
		let t = this.rules.block.blockquote.exec(e);
		if (t) {
			let e = Ft(t[0], "\n").split("\n"), n = "", r = "", i = [];
			for (; e.length > 0;) {
				let t = !1, a = [], o;
				for (o = 0; o < e.length; o++) if (this.rules.other.blockquoteStart.test(e[o])) a.push(e[o]), t = !0;
				else if (!t) a.push(e[o]);
				else break;
				e = e.slice(o);
				let s = a.join("\n"), c = s.replace(this.rules.other.blockquoteSetextReplace, "\n    $1").replace(this.rules.other.blockquoteSetextReplace2, "");
				n = n ? `${n}
${s}` : s, r = r ? `${r}
${c}` : c;
				let l = this.lexer.state.top;
				if (this.lexer.state.top = !0, this.lexer.blockTokens(c, i, !0), this.lexer.state.top = l, e.length === 0) break;
				let u = i.at(-1);
				if (u?.type === "code") break;
				if (u?.type === "blockquote") {
					let t = u, a = t.raw + "\n" + e.join("\n"), o = this.blockquote(a);
					i[i.length - 1] = o, n = n.substring(0, n.length - t.raw.length) + o.raw, r = r.substring(0, r.length - t.text.length) + o.text;
					break;
				} else if (u?.type === "list") {
					let t = u, a = t.raw + "\n" + e.join("\n"), o = this.list(a);
					i[i.length - 1] = o, n = n.substring(0, n.length - u.raw.length) + o.raw, r = r.substring(0, r.length - t.raw.length) + o.raw, e = a.substring(i.at(-1).raw.length).split("\n");
					continue;
				}
			}
			return {
				type: "blockquote",
				raw: n,
				tokens: i,
				text: r
			};
		}
	}
	list(e) {
		let t = this.rules.block.list.exec(e);
		if (t) {
			let n = t[1].trim(), r = n.length > 1, i = {
				type: "list",
				raw: "",
				ordered: r,
				start: r ? +n.slice(0, -1) : "",
				loose: !1,
				items: []
			};
			n = r ? `\\d{1,9}\\${n.slice(-1)}` : `\\${n}`, this.options.pedantic && (n = r ? n : "[*+-]");
			let a = this.rules.other.listItemRegex(n), o = !1;
			for (; e;) {
				let n = !1, r = "", s = "";
				if (!(t = a.exec(e)) || this.rules.block.hr.test(e)) break;
				r = t[0], e = e.substring(r.length);
				let c = Rt(t[2].split("\n", 1)[0], t[1].length), l = e.split("\n", 1)[0], u = !c.trim(), d = 0;
				if (this.options.pedantic ? (d = 2, s = c.trimStart()) : u ? d = t[1].length + 1 : (d = c.search(this.rules.other.nonSpaceChar), d = d > 4 ? 1 : d, s = c.slice(d), d += t[1].length), u && this.rules.other.blankLine.test(l) && (r += l + "\n", e = e.substring(l.length + 1), n = !0), !n) {
					let t = this.rules.other.nextBulletRegex(d), n = this.rules.other.hrRegex(d), i = this.rules.other.fencesBeginRegex(d), a = this.rules.other.headingBeginRegex(d), o = this.rules.other.htmlBeginRegex(d), f = this.rules.other.blockquoteBeginRegex(d);
					for (; e;) {
						let p = e.split("\n", 1)[0], m;
						if (l = p, this.options.pedantic ? (l = l.replace(this.rules.other.listReplaceNesting, "  "), m = l) : m = l.replace(this.rules.other.tabCharGlobal, "    "), i.test(l) || a.test(l) || o.test(l) || f.test(l) || t.test(l) || n.test(l)) break;
						if (m.search(this.rules.other.nonSpaceChar) >= d || !l.trim()) s += "\n" + m.slice(d);
						else {
							if (u || c.replace(this.rules.other.tabCharGlobal, "    ").search(this.rules.other.nonSpaceChar) >= 4 || i.test(c) || a.test(c) || n.test(c)) break;
							s += "\n" + l;
						}
						u = !l.trim(), r += p + "\n", e = e.substring(p.length + 1), c = m.slice(d);
					}
				}
				i.loose || (o ? i.loose = !0 : this.rules.other.doubleBlankLine.test(r) && (o = !0)), i.items.push({
					type: "list_item",
					raw: r,
					task: !!this.options.gfm && this.rules.other.listIsTask.test(s),
					loose: !1,
					text: s,
					tokens: []
				}), i.raw += r;
			}
			let s = i.items.at(-1);
			if (s) s.raw = s.raw.trimEnd(), s.text = s.text.trimEnd();
			else return;
			i.raw = i.raw.trimEnd();
			for (let e of i.items) {
				this.lexer.state.top = !1, e.tokens = this.lexer.blockTokens(e.text, []);
				let t = e.tokens[0];
				if (e.task && (t?.type === "text" || t?.type === "paragraph")) {
					e.text = e.text.replace(this.rules.other.listReplaceTask, ""), t.raw = t.raw.replace(this.rules.other.listReplaceTask, ""), t.text = t.text.replace(this.rules.other.listReplaceTask, "");
					for (let e = this.lexer.inlineQueue.length - 1; e >= 0; e--) if (this.rules.other.listIsTask.test(this.lexer.inlineQueue[e].src)) {
						this.lexer.inlineQueue[e].src = this.lexer.inlineQueue[e].src.replace(this.rules.other.listReplaceTask, "");
						break;
					}
					let n = this.rules.other.listTaskCheckbox.exec(e.raw);
					if (n) {
						let t = {
							type: "checkbox",
							raw: n[0] + " ",
							checked: n[0] !== "[ ]"
						};
						e.checked = t.checked, i.loose ? e.tokens[0] && ["paragraph", "text"].includes(e.tokens[0].type) && "tokens" in e.tokens[0] && e.tokens[0].tokens ? (e.tokens[0].raw = t.raw + e.tokens[0].raw, e.tokens[0].text = t.raw + e.tokens[0].text, e.tokens[0].tokens.unshift(t)) : e.tokens.unshift({
							type: "paragraph",
							raw: t.raw,
							text: t.raw,
							tokens: [t]
						}) : e.tokens.unshift(t);
					}
				} else e.task &&= !1;
				if (!i.loose) {
					let t = e.tokens.filter((e) => e.type === "space");
					i.loose = t.length > 0 && t.some((e) => this.rules.other.anyLine.test(e.raw));
				}
			}
			if (i.loose) for (let e of i.items) {
				e.loose = !0;
				for (let t of e.tokens) t.type === "text" && (t.type = "paragraph");
			}
			return i;
		}
	}
	html(e) {
		let t = this.rules.block.html.exec(e);
		if (t) {
			let e = It(t[0]);
			return {
				type: "html",
				block: !0,
				raw: e,
				pre: t[1] === "pre" || t[1] === "script" || t[1] === "style",
				text: e
			};
		}
	}
	def(e) {
		let t = this.rules.block.def.exec(e);
		if (t) {
			let e = t[1].toLowerCase().replace(this.rules.other.multipleSpaceGlobal, " "), n = t[2] ? t[2].replace(this.rules.other.hrefBrackets, "$1").replace(this.rules.inline.anyPunctuation, "$1") : "", r = t[3] ? t[3].substring(1, t[3].length - 1).replace(this.rules.inline.anyPunctuation, "$1") : t[3];
			return {
				type: "def",
				tag: e,
				raw: Ft(t[0], "\n"),
				href: n,
				title: r
			};
		}
	}
	table(e) {
		let t = this.rules.block.table.exec(e);
		if (!t || !this.rules.other.tableDelimiter.test(t[2])) return;
		let n = Pt(t[1]), r = t[2].replace(this.rules.other.tableAlignChars, "").split("|"), i = t[3]?.trim() ? t[3].replace(this.rules.other.tableRowBlankLine, "").split("\n") : [], a = {
			type: "table",
			raw: Ft(t[0], "\n"),
			header: [],
			align: [],
			rows: []
		};
		if (n.length === r.length) {
			for (let e of r) this.rules.other.tableAlignRight.test(e) ? a.align.push("right") : this.rules.other.tableAlignCenter.test(e) ? a.align.push("center") : this.rules.other.tableAlignLeft.test(e) ? a.align.push("left") : a.align.push(null);
			for (let e = 0; e < n.length; e++) a.header.push({
				text: n[e],
				tokens: this.lexer.inline(n[e]),
				header: !0,
				align: a.align[e]
			});
			for (let e of i) a.rows.push(Pt(e, a.header.length).map((e, t) => ({
				text: e,
				tokens: this.lexer.inline(e),
				header: !1,
				align: a.align[t]
			})));
			return a;
		}
	}
	lheading(e) {
		let t = this.rules.block.lheading.exec(e);
		if (t) {
			let e = t[1].trim();
			return {
				type: "heading",
				raw: Ft(t[0], "\n"),
				depth: t[2].charAt(0) === "=" ? 1 : 2,
				text: e,
				tokens: this.lexer.inline(e)
			};
		}
	}
	paragraph(e) {
		let t = this.rules.block.paragraph.exec(e);
		if (t) {
			let e = t[1].charAt(t[1].length - 1) === "\n" ? t[1].slice(0, -1) : t[1];
			return {
				type: "paragraph",
				raw: t[0],
				text: e,
				tokens: this.lexer.inline(e)
			};
		}
	}
	text(e) {
		let t = this.rules.block.text.exec(e);
		if (t) return {
			type: "text",
			raw: t[0],
			text: t[0],
			tokens: this.lexer.inline(t[0])
		};
	}
	escape(e) {
		let t = this.rules.inline.escape.exec(e);
		if (t) return {
			type: "escape",
			raw: t[0],
			text: t[1]
		};
	}
	tag(e) {
		let t = this.rules.inline.tag.exec(e);
		if (t) return !this.lexer.state.inLink && this.rules.other.startATag.test(t[0]) ? this.lexer.state.inLink = !0 : this.lexer.state.inLink && this.rules.other.endATag.test(t[0]) && (this.lexer.state.inLink = !1), !this.lexer.state.inRawBlock && this.rules.other.startPreScriptTag.test(t[0]) ? this.lexer.state.inRawBlock = !0 : this.lexer.state.inRawBlock && this.rules.other.endPreScriptTag.test(t[0]) && (this.lexer.state.inRawBlock = !1), {
			type: "html",
			raw: t[0],
			inLink: this.lexer.state.inLink,
			inRawBlock: this.lexer.state.inRawBlock,
			block: !1,
			text: t[0]
		};
	}
	link(e) {
		let t = this.rules.inline.link.exec(e);
		if (t) {
			let e = t[2].trim();
			if (!this.options.pedantic && this.rules.other.startAngleBracket.test(e)) {
				if (!this.rules.other.endAngleBracket.test(e)) return;
				let t = Ft(e.slice(0, -1), "\\");
				if ((e.length - t.length) % 2 == 0) return;
			} else {
				let e = Lt(t[2], "()");
				if (e === -2) return;
				if (e > -1) {
					let n = (t[0].indexOf("!") === 0 ? 5 : 4) + t[1].length + e;
					t[2] = t[2].substring(0, e), t[0] = t[0].substring(0, n).trim(), t[3] = "";
				}
			}
			let n = t[2], r = "";
			if (this.options.pedantic) {
				let e = this.rules.other.pedanticHrefTitle.exec(n);
				e && (n = e[1], r = e[3]);
			} else r = t[3] ? t[3].slice(1, -1) : "";
			return n = n.trim(), this.rules.other.startAngleBracket.test(n) && (n = this.options.pedantic && !this.rules.other.endAngleBracket.test(e) ? n.slice(1) : n.slice(1, -1)), zt(t, {
				href: n && n.replace(this.rules.inline.anyPunctuation, "$1"),
				title: r && r.replace(this.rules.inline.anyPunctuation, "$1")
			}, t[0], this.lexer, this.rules);
		}
	}
	reflink(e, t) {
		let n;
		if ((n = this.rules.inline.reflink.exec(e)) || (n = this.rules.inline.nolink.exec(e))) {
			let e = t[(n[2] || n[1]).replace(this.rules.other.multipleSpaceGlobal, " ").toLowerCase()];
			if (!e) {
				let e = n[0].charAt(0);
				return {
					type: "text",
					raw: e,
					text: e
				};
			}
			return zt(n, e, n[0], this.lexer, this.rules);
		}
	}
	emStrong(e, t, n = "") {
		let r = this.rules.inline.emStrongLDelim.exec(e);
		if (!(!r || !r[1] && !r[2] && !r[3] && !r[4] || r[4] && n.match(this.rules.other.unicodeAlphaNumeric)) && (!(r[1] || r[3]) || !n || this.rules.inline.punctuation.exec(n))) {
			let n = [...r[0]].length - 1, i, a, o = n, s = 0, c = r[0][0] === "*" ? this.rules.inline.emStrongRDelimAst : this.rules.inline.emStrongRDelimUnd;
			for (c.lastIndex = 0, t = t.slice(-1 * e.length + n); (r = c.exec(t)) !== null;) {
				if (i = r[1] || r[2] || r[3] || r[4] || r[5] || r[6], !i) continue;
				if (a = [...i].length, r[3] || r[4]) {
					o += a;
					continue;
				} else if ((r[5] || r[6]) && n % 3 && !((n + a) % 3)) {
					s += a;
					continue;
				}
				if (o -= a, o > 0) continue;
				a = Math.min(a, a + o + s);
				let t = [...r[0]][0].length, c = e.slice(0, n + r.index + t + a);
				if (Math.min(n, a) % 2) {
					let e = c.slice(1, -1);
					return {
						type: "em",
						raw: c,
						text: e,
						tokens: this.lexer.inlineTokens(e)
					};
				}
				let l = c.slice(2, -2);
				return {
					type: "strong",
					raw: c,
					text: l,
					tokens: this.lexer.inlineTokens(l)
				};
			}
		}
	}
	codespan(e) {
		let t = this.rules.inline.code.exec(e);
		if (t) {
			let e = t[2].replace(this.rules.other.newLineCharGlobal, " "), n = this.rules.other.nonSpaceChar.test(e), r = this.rules.other.startingSpaceChar.test(e) && this.rules.other.endingSpaceChar.test(e);
			return n && r && (e = e.substring(1, e.length - 1)), {
				type: "codespan",
				raw: t[0],
				text: e
			};
		}
	}
	br(e) {
		let t = this.rules.inline.br.exec(e);
		if (t) return {
			type: "br",
			raw: t[0]
		};
	}
	del(e, t, n = "") {
		let r = this.rules.inline.delLDelim.exec(e);
		if (r && (!r[1] || !n || this.rules.inline.punctuation.exec(n))) {
			let n = [...r[0]].length - 1, i, a, o = n, s = this.rules.inline.delRDelim;
			for (s.lastIndex = 0, t = t.slice(-1 * e.length + n); (r = s.exec(t)) !== null;) {
				if (i = r[1] || r[2] || r[3] || r[4] || r[5] || r[6], !i || (a = [...i].length, a !== n)) continue;
				if (r[3] || r[4]) {
					o += a;
					continue;
				}
				if (o -= a, o > 0) continue;
				a = Math.min(a, a + o);
				let t = [...r[0]][0].length, s = e.slice(0, n + r.index + t + a), c = s.slice(n, -n);
				return {
					type: "del",
					raw: s,
					text: c,
					tokens: this.lexer.inlineTokens(c)
				};
			}
		}
	}
	autolink(e) {
		let t = this.rules.inline.autolink.exec(e);
		if (t) {
			let e, n;
			return t[2] === "@" ? (e = t[1], n = "mailto:" + e) : (e = t[1], n = e), {
				type: "link",
				raw: t[0],
				text: e,
				href: n,
				tokens: [{
					type: "text",
					raw: e,
					text: e
				}]
			};
		}
	}
	url(e) {
		let t;
		if (t = this.rules.inline.url.exec(e)) {
			let e, n;
			if (t[2] === "@") e = t[0], n = "mailto:" + e;
			else {
				let r;
				do
					r = t[0], t[0] = this.rules.inline._backpedal.exec(t[0])?.[0] ?? "";
				while (r !== t[0]);
				e = t[0], n = t[1] === "www." ? "http://" + t[0] : t[0];
			}
			return {
				type: "link",
				raw: t[0],
				text: e,
				href: n,
				tokens: [{
					type: "text",
					raw: e,
					text: e
				}]
			};
		}
	}
	inlineText(e) {
		let t = this.rules.inline.text.exec(e);
		if (t) {
			let e = this.lexer.state.inRawBlock;
			return {
				type: "text",
				raw: t[0],
				text: t[0],
				escaped: e
			};
		}
	}
}, Ht = class e {
	tokens;
	options;
	state;
	inlineQueue;
	tokenizer;
	constructor(e) {
		this.tokens = [], this.tokens.links = Object.create(null), this.options = e || ve, this.options.tokenizer = this.options.tokenizer || new Vt(), this.tokenizer = this.options.tokenizer, this.tokenizer.options = this.options, this.tokenizer.lexer = this, this.inlineQueue = [], this.state = {
			inLink: !1,
			inRawBlock: !1,
			top: !0
		};
		let t = {
			other: Ce,
			block: Ot.normal,
			inline: kt.normal
		};
		this.options.pedantic ? (t.block = Ot.pedantic, t.inline = kt.pedantic) : this.options.gfm && (t.block = Ot.gfm, this.options.breaks ? t.inline = kt.breaks : t.inline = kt.gfm), this.tokenizer.rules = t;
	}
	static get rules() {
		return {
			block: Ot,
			inline: kt
		};
	}
	static lex(t, n) {
		return new e(n).lex(t);
	}
	static lexInline(t, n) {
		return new e(n).inlineTokens(t);
	}
	lex(e) {
		e = e.replace(Ce.carriageReturn, "\n"), this.blockTokens(e, this.tokens);
		for (let e = 0; e < this.inlineQueue.length; e++) {
			let t = this.inlineQueue[e];
			this.inlineTokens(t.src, t.tokens);
		}
		return this.inlineQueue = [], this.tokens;
	}
	blockTokens(e, t = [], n = !1) {
		this.tokenizer.lexer = this, this.options.pedantic && (e = e.replace(Ce.tabCharGlobal, "    ").replace(Ce.spaceLine, ""));
		let r = Infinity;
		for (; e;) {
			if (e.length < r) r = e.length;
			else {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
			let i;
			if (this.options.extensions?.block?.some((n) => (i = n.call({ lexer: this }, e, t)) ? (e = e.substring(i.raw.length), t.push(i), !0) : !1)) continue;
			if (i = this.tokenizer.space(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				i.raw.length === 1 && n !== void 0 ? n.raw += "\n" : t.push(i);
				continue;
			}
			if (i = this.tokenizer.code(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				n?.type === "paragraph" || n?.type === "text" ? (n.raw += (n.raw.endsWith("\n") ? "" : "\n") + i.raw, n.text += "\n" + i.text, this.inlineQueue.at(-1).src = n.text) : t.push(i);
				continue;
			}
			if (i = this.tokenizer.fences(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.heading(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.hr(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.blockquote(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.list(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.html(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.def(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				n?.type === "paragraph" || n?.type === "text" ? (n.raw += (n.raw.endsWith("\n") ? "" : "\n") + i.raw, n.text += "\n" + i.raw, this.inlineQueue.at(-1).src = n.text) : this.tokens.links[i.tag] || (this.tokens.links[i.tag] = {
					href: i.href,
					title: i.title
				}, t.push(i));
				continue;
			}
			if (i = this.tokenizer.table(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			if (i = this.tokenizer.lheading(e)) {
				e = e.substring(i.raw.length), t.push(i);
				continue;
			}
			let a = e;
			if (this.options.extensions?.startBlock) {
				let t = Infinity, n = e.slice(1), r;
				this.options.extensions.startBlock.forEach((e) => {
					r = e.call({ lexer: this }, n), typeof r == "number" && r >= 0 && (t = Math.min(t, r));
				}), t < Infinity && t >= 0 && (a = e.substring(0, t + 1));
			}
			if (this.state.top && (i = this.tokenizer.paragraph(a))) {
				let r = t.at(-1);
				n && r?.type === "paragraph" ? (r.raw += (r.raw.endsWith("\n") ? "" : "\n") + i.raw, r.text += "\n" + i.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = r.text) : t.push(i), n = a.length !== e.length, e = e.substring(i.raw.length);
				continue;
			}
			if (i = this.tokenizer.text(e)) {
				e = e.substring(i.raw.length);
				let n = t.at(-1);
				n?.type === "text" ? (n.raw += (n.raw.endsWith("\n") ? "" : "\n") + i.raw, n.text += "\n" + i.text, this.inlineQueue.pop(), this.inlineQueue.at(-1).src = n.text) : t.push(i);
				continue;
			}
			if (e) {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
		}
		return this.state.top = !0, t;
	}
	inline(e, t = []) {
		return this.inlineQueue.push({
			src: e,
			tokens: t
		}), t;
	}
	inlineTokens(e, t = []) {
		this.tokenizer.lexer = this;
		let n = e;
		if (this.tokens.links) {
			let e = Object.keys(this.tokens.links);
			e.length > 0 && (n = n.replace(this.tokenizer.rules.inline.reflinkSearch, (t) => e.includes(t.slice(t.lastIndexOf("[") + 1, -1)) ? "[" + "a".repeat(t.length - 2) + "]" : t));
		}
		n = n.replace(this.tokenizer.rules.inline.anyPunctuation, "++"), n = n.replace(this.tokenizer.rules.inline.blockSkip, (e, t, n) => {
			let r = n ? n.length : 0;
			return e.slice(0, r) + "[" + "a".repeat(e.length - r - 2) + "]";
		}), n = this.options.hooks?.emStrongMask?.call({ lexer: this }, n) ?? n;
		let r = !1, i = "", a = Infinity;
		for (; e;) {
			if (e.length < a) a = e.length;
			else {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
			r || (i = ""), r = !1;
			let o;
			if (this.options.extensions?.inline?.some((n) => (o = n.call({ lexer: this }, e, t)) ? (e = e.substring(o.raw.length), t.push(o), !0) : !1)) continue;
			if (o = this.tokenizer.escape(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.tag(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.link(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.reflink(e, this.tokens.links)) {
				e = e.substring(o.raw.length);
				let n = t.at(-1);
				o.type === "text" && n?.type === "text" ? (n.raw += o.raw, n.text += o.text) : t.push(o);
				continue;
			}
			if (o = this.tokenizer.emStrong(e, n, i)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.codespan(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.br(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.del(e, n, i)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (o = this.tokenizer.autolink(e)) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			if (!this.state.inLink && (o = this.tokenizer.url(e))) {
				e = e.substring(o.raw.length), t.push(o);
				continue;
			}
			let s = e;
			if (this.options.extensions?.startInline) {
				let t = Infinity, n = e.slice(1), r;
				this.options.extensions.startInline.forEach((e) => {
					r = e.call({ lexer: this }, n), typeof r == "number" && r >= 0 && (t = Math.min(t, r));
				}), t < Infinity && t >= 0 && (s = e.substring(0, t + 1));
			}
			if (o = this.tokenizer.inlineText(s)) {
				e = e.substring(o.raw.length), o.raw.slice(-1) !== "_" && (i = o.raw.slice(-1)), r = !0;
				let n = t.at(-1);
				n?.type === "text" ? (n.raw += o.raw, n.text += o.text) : t.push(o);
				continue;
			}
			if (e) {
				this.infiniteLoopError(e.charCodeAt(0));
				break;
			}
		}
		return t;
	}
	infiniteLoopError(e) {
		let t = "Infinite loop on byte: " + e;
		if (this.options.silent) console.error(t);
		else throw Error(t);
	}
}, Ut = class {
	options;
	parser;
	constructor(e) {
		this.options = e || ve;
	}
	space(e) {
		return "";
	}
	code({ text: e, lang: t, escaped: n }) {
		let r = (t || "").match(Ce.notSpaceStart)?.[0], i = e.replace(Ce.endingNewline, "") + "\n";
		return r ? "<pre><code class=\"language-" + Mt(r) + "\">" + (n ? i : Mt(i, !0)) + "</code></pre>\n" : "<pre><code>" + (n ? i : Mt(i, !0)) + "</code></pre>\n";
	}
	blockquote({ tokens: e }) {
		return `<blockquote>
${this.parser.parse(e)}</blockquote>
`;
	}
	html({ text: e }) {
		return e;
	}
	def(e) {
		return "";
	}
	heading({ tokens: e, depth: t }) {
		return `<h${t}>${this.parser.parseInline(e)}</h${t}>
`;
	}
	hr(e) {
		return "<hr>\n";
	}
	list(e) {
		let t = e.ordered, n = e.start, r = "";
		for (let t = 0; t < e.items.length; t++) {
			let n = e.items[t];
			r += this.listitem(n);
		}
		let i = t ? "ol" : "ul", a = t && n !== 1 ? " start=\"" + n + "\"" : "";
		return "<" + i + a + ">\n" + r + "</" + i + ">\n";
	}
	listitem(e) {
		return `<li>${this.parser.parse(e.tokens)}</li>
`;
	}
	checkbox({ checked: e }) {
		return "<input " + (e ? "checked=\"\" " : "") + "disabled=\"\" type=\"checkbox\"> ";
	}
	paragraph({ tokens: e }) {
		return `<p>${this.parser.parseInline(e)}</p>
`;
	}
	table(e) {
		let t = "", n = "";
		for (let t = 0; t < e.header.length; t++) n += this.tablecell(e.header[t]);
		t += this.tablerow({ text: n });
		let r = "";
		for (let t = 0; t < e.rows.length; t++) {
			let i = e.rows[t];
			n = "";
			for (let e = 0; e < i.length; e++) n += this.tablecell(i[e]);
			r += this.tablerow({ text: n });
		}
		return r &&= `<tbody>${r}</tbody>`, "<table>\n<thead>\n" + t + "</thead>\n" + r + "</table>\n";
	}
	tablerow({ text: e }) {
		return `<tr>
${e}</tr>
`;
	}
	tablecell(e) {
		let t = this.parser.parseInline(e.tokens), n = e.header ? "th" : "td";
		return (e.align ? `<${n} align="${e.align}">` : `<${n}>`) + t + `</${n}>
`;
	}
	strong({ tokens: e }) {
		return `<strong>${this.parser.parseInline(e)}</strong>`;
	}
	em({ tokens: e }) {
		return `<em>${this.parser.parseInline(e)}</em>`;
	}
	codespan({ text: e }) {
		return `<code>${Mt(e, !0)}</code>`;
	}
	br(e) {
		return "<br>";
	}
	del({ tokens: e }) {
		return `<del>${this.parser.parseInline(e)}</del>`;
	}
	link({ href: e, title: t, tokens: n }) {
		let r = this.parser.parseInline(n), i = Nt(e);
		if (i === null) return r;
		e = i;
		let a = "<a href=\"" + e + "\"";
		return t && (a += " title=\"" + Mt(t) + "\""), a += ">" + r + "</a>", a;
	}
	image({ href: e, title: t, text: n, tokens: r }) {
		r && (n = this.parser.parseInline(r, this.parser.textRenderer));
		let i = Nt(e);
		if (i === null) return Mt(n);
		e = i;
		let a = `<img src="${e}" alt="${Mt(n)}"`;
		return t && (a += ` title="${Mt(t)}"`), a += ">", a;
	}
	text(e) {
		return "tokens" in e && e.tokens ? this.parser.parseInline(e.tokens) : "escaped" in e && e.escaped ? e.text : Mt(e.text);
	}
}, Wt = class {
	strong({ text: e }) {
		return e;
	}
	em({ text: e }) {
		return e;
	}
	codespan({ text: e }) {
		return e;
	}
	del({ text: e }) {
		return e;
	}
	html({ text: e }) {
		return e;
	}
	text({ text: e }) {
		return e;
	}
	link({ text: e }) {
		return "" + e;
	}
	image({ text: e }) {
		return "" + e;
	}
	br() {
		return "";
	}
	checkbox({ raw: e }) {
		return e;
	}
}, Gt = class e {
	options;
	renderer;
	textRenderer;
	constructor(e) {
		this.options = e || ve, this.options.renderer = this.options.renderer || new Ut(), this.renderer = this.options.renderer, this.renderer.options = this.options, this.renderer.parser = this, this.textRenderer = new Wt();
	}
	static parse(t, n) {
		return new e(n).parse(t);
	}
	static parseInline(t, n) {
		return new e(n).parseInline(t);
	}
	parse(e) {
		this.renderer.parser = this;
		let t = "";
		for (let n = 0; n < e.length; n++) {
			let r = e[n];
			if (this.options.extensions?.renderers?.[r.type]) {
				let e = r, n = this.options.extensions.renderers[e.type].call({ parser: this }, e);
				if (n !== !1 || ![
					"space",
					"hr",
					"heading",
					"code",
					"table",
					"blockquote",
					"list",
					"html",
					"def",
					"paragraph",
					"text"
				].includes(e.type)) {
					t += n || "";
					continue;
				}
			}
			let i = r;
			switch (i.type) {
				case "space":
					t += this.renderer.space(i);
					break;
				case "hr":
					t += this.renderer.hr(i);
					break;
				case "heading":
					t += this.renderer.heading(i);
					break;
				case "code":
					t += this.renderer.code(i);
					break;
				case "table":
					t += this.renderer.table(i);
					break;
				case "blockquote":
					t += this.renderer.blockquote(i);
					break;
				case "list":
					t += this.renderer.list(i);
					break;
				case "checkbox":
					t += this.renderer.checkbox(i);
					break;
				case "html":
					t += this.renderer.html(i);
					break;
				case "def":
					t += this.renderer.def(i);
					break;
				case "paragraph":
					t += this.renderer.paragraph(i);
					break;
				case "text":
					t += this.renderer.text(i);
					break;
				default: {
					let e = "Token with \"" + i.type + "\" type was not found.";
					if (this.options.silent) return console.error(e), "";
					throw Error(e);
				}
			}
		}
		return t;
	}
	parseInline(e, t = this.renderer) {
		this.renderer.parser = this;
		let n = "";
		for (let r = 0; r < e.length; r++) {
			let i = e[r];
			if (this.options.extensions?.renderers?.[i.type]) {
				let e = this.options.extensions.renderers[i.type].call({ parser: this }, i);
				if (e !== !1 || ![
					"escape",
					"html",
					"link",
					"image",
					"strong",
					"em",
					"codespan",
					"br",
					"del",
					"text"
				].includes(i.type)) {
					n += e || "";
					continue;
				}
			}
			let a = i;
			switch (a.type) {
				case "escape":
					n += t.text(a);
					break;
				case "html":
					n += t.html(a);
					break;
				case "link":
					n += t.link(a);
					break;
				case "image":
					n += t.image(a);
					break;
				case "checkbox":
					n += t.checkbox(a);
					break;
				case "strong":
					n += t.strong(a);
					break;
				case "em":
					n += t.em(a);
					break;
				case "codespan":
					n += t.codespan(a);
					break;
				case "br":
					n += t.br(a);
					break;
				case "del":
					n += t.del(a);
					break;
				case "text":
					n += t.text(a);
					break;
				default: {
					let e = "Token with \"" + a.type + "\" type was not found.";
					if (this.options.silent) return console.error(e), "";
					throw Error(e);
				}
			}
		}
		return n;
	}
}, Kt = class {
	options;
	block;
	constructor(e) {
		this.options = e || ve;
	}
	static passThroughHooks = /* @__PURE__ */ new Set([
		"preprocess",
		"postprocess",
		"processAllTokens",
		"emStrongMask"
	]);
	static passThroughHooksRespectAsync = /* @__PURE__ */ new Set([
		"preprocess",
		"postprocess",
		"processAllTokens"
	]);
	preprocess(e) {
		return e;
	}
	postprocess(e) {
		return e;
	}
	processAllTokens(e) {
		return e;
	}
	emStrongMask(e) {
		return e;
	}
	provideLexer(e = this.block) {
		return e ? Ht.lex : Ht.lexInline;
	}
	provideParser(e = this.block) {
		return e ? Gt.parse : Gt.parseInline;
	}
}, qt = new class {
	defaults = _e();
	options = this.setOptions;
	parse = this.parseMarkdown(!0);
	parseInline = this.parseMarkdown(!1);
	Parser = Gt;
	Renderer = Ut;
	TextRenderer = Wt;
	Lexer = Ht;
	Tokenizer = Vt;
	Hooks = Kt;
	constructor(...e) {
		this.use(...e);
	}
	walkTokens(e, t) {
		let n = [];
		for (let r of e) switch (n = n.concat(t.call(this, r)), r.type) {
			case "table": {
				let e = r;
				for (let r of e.header) n = n.concat(this.walkTokens(r.tokens, t));
				for (let r of e.rows) for (let e of r) n = n.concat(this.walkTokens(e.tokens, t));
				break;
			}
			case "list": {
				let e = r;
				n = n.concat(this.walkTokens(e.items, t));
				break;
			}
			default: {
				let e = r;
				this.defaults.extensions?.childTokens?.[e.type] ? this.defaults.extensions.childTokens[e.type].forEach((r) => {
					let i = e[r].flat(Infinity);
					n = n.concat(this.walkTokens(i, t));
				}) : e.tokens && (n = n.concat(this.walkTokens(e.tokens, t)));
			}
		}
		return n;
	}
	use(...e) {
		let t = this.defaults.extensions || {
			renderers: {},
			childTokens: {}
		};
		return e.forEach((e) => {
			let n = { ...e };
			if (n.async = this.defaults.async || n.async || !1, e.extensions && (e.extensions.forEach((e) => {
				if (!e.name) throw Error("extension name required");
				if ("renderer" in e) {
					let n = t.renderers[e.name];
					n ? t.renderers[e.name] = function(...t) {
						let r = e.renderer.apply(this, t);
						return r === !1 && (r = n.apply(this, t)), r;
					} : t.renderers[e.name] = e.renderer;
				}
				if ("tokenizer" in e) {
					if (!e.level || e.level !== "block" && e.level !== "inline") throw Error("extension level must be 'block' or 'inline'");
					let n = t[e.level];
					n ? n.unshift(e.tokenizer) : t[e.level] = [e.tokenizer], e.start && (e.level === "block" ? t.startBlock ? t.startBlock.push(e.start) : t.startBlock = [e.start] : e.level === "inline" && (t.startInline ? t.startInline.push(e.start) : t.startInline = [e.start]));
				}
				"childTokens" in e && e.childTokens && (t.childTokens[e.name] = e.childTokens);
			}), n.extensions = t), e.renderer) {
				let t = this.defaults.renderer || new Ut(this.defaults);
				for (let n in e.renderer) {
					if (!(n in t)) throw Error(`renderer '${n}' does not exist`);
					if (["options", "parser"].includes(n)) continue;
					let r = n, i = e.renderer[r], a = t[r];
					t[r] = (...e) => {
						let n = i.apply(t, e);
						return n === !1 && (n = a.apply(t, e)), n || "";
					};
				}
				n.renderer = t;
			}
			if (e.tokenizer) {
				let t = this.defaults.tokenizer || new Vt(this.defaults);
				for (let n in e.tokenizer) {
					if (!(n in t)) throw Error(`tokenizer '${n}' does not exist`);
					if ([
						"options",
						"rules",
						"lexer"
					].includes(n)) continue;
					let r = n, i = e.tokenizer[r], a = t[r];
					t[r] = (...e) => {
						let n = i.apply(t, e);
						return n === !1 && (n = a.apply(t, e)), n;
					};
				}
				n.tokenizer = t;
			}
			if (e.hooks) {
				let t = this.defaults.hooks || new Kt();
				for (let n in e.hooks) {
					if (!(n in t)) throw Error(`hook '${n}' does not exist`);
					if (["options", "block"].includes(n)) continue;
					let r = n, i = e.hooks[r], a = t[r];
					Kt.passThroughHooks.has(n) ? t[r] = (e) => {
						if (this.defaults.async && Kt.passThroughHooksRespectAsync.has(n)) return (async () => {
							let n = await i.call(t, e);
							return a.call(t, n);
						})();
						let r = i.call(t, e);
						return a.call(t, r);
					} : t[r] = (...e) => {
						if (this.defaults.async) return (async () => {
							let n = await i.apply(t, e);
							return n === !1 && (n = await a.apply(t, e)), n;
						})();
						let n = i.apply(t, e);
						return n === !1 && (n = a.apply(t, e)), n;
					};
				}
				n.hooks = t;
			}
			if (e.walkTokens) {
				let t = this.defaults.walkTokens, r = e.walkTokens;
				n.walkTokens = function(e) {
					let n = [];
					return n.push(r.call(this, e)), t && (n = n.concat(t.call(this, e))), n;
				};
			}
			this.defaults = {
				...this.defaults,
				...n
			};
		}), this;
	}
	setOptions(e) {
		return this.defaults = {
			...this.defaults,
			...e
		}, this;
	}
	lexer(e, t) {
		return Ht.lex(e, t ?? this.defaults);
	}
	parser(e, t) {
		return Gt.parse(e, t ?? this.defaults);
	}
	parseMarkdown(e) {
		return (t, n) => {
			let r = { ...n }, i = {
				...this.defaults,
				...r
			}, a = this.onError(!!i.silent, !!i.async);
			if (this.defaults.async === !0 && r.async === !1) return a(/* @__PURE__ */ Error("marked(): The async option was set to true by an extension. Remove async: false from the parse options object to return a Promise."));
			if (typeof t > "u" || t === null) return a(/* @__PURE__ */ Error("marked(): input parameter is undefined or null"));
			if (typeof t != "string") return a(/* @__PURE__ */ Error("marked(): input parameter is of type " + Object.prototype.toString.call(t) + ", string expected"));
			if (i.hooks && (i.hooks.options = i, i.hooks.block = e), i.async) return (async () => {
				let n = i.hooks ? await i.hooks.preprocess(t) : t, r = await (i.hooks ? await i.hooks.provideLexer(e) : e ? Ht.lex : Ht.lexInline)(n, i), a = i.hooks ? await i.hooks.processAllTokens(r) : r;
				i.walkTokens && await Promise.all(this.walkTokens(a, i.walkTokens));
				let o = await (i.hooks ? await i.hooks.provideParser(e) : e ? Gt.parse : Gt.parseInline)(a, i);
				return i.hooks ? await i.hooks.postprocess(o) : o;
			})().catch(a);
			try {
				i.hooks && (t = i.hooks.preprocess(t));
				let n = (i.hooks ? i.hooks.provideLexer(e) : e ? Ht.lex : Ht.lexInline)(t, i);
				i.hooks && (n = i.hooks.processAllTokens(n)), i.walkTokens && this.walkTokens(n, i.walkTokens);
				let r = (i.hooks ? i.hooks.provideParser(e) : e ? Gt.parse : Gt.parseInline)(n, i);
				return i.hooks && (r = i.hooks.postprocess(r)), r;
			} catch (e) {
				return a(e);
			}
		};
	}
	onError(e, t) {
		return (n) => {
			if (n.message += "\nPlease report this to https://github.com/markedjs/marked.", e) {
				let e = "<p>An error occurred:</p><pre>" + Mt(n.message + "", !0) + "</pre>";
				return t ? Promise.resolve(e) : e;
			}
			if (t) return Promise.reject(n);
			throw n;
		};
	}
}();
function Jt(e, t) {
	return qt.parse(e, t);
}
Jt.options = Jt.setOptions = function(e) {
	return qt.setOptions(e), Jt.defaults = qt.defaults, ye(Jt.defaults), Jt;
}, Jt.getDefaults = _e, Jt.defaults = ve, Jt.use = function(...e) {
	return qt.use(...e), Jt.defaults = qt.defaults, ye(Jt.defaults), Jt;
}, Jt.walkTokens = function(e, t) {
	return qt.walkTokens(e, t);
}, Jt.parseInline = qt.parseInline, Jt.Parser = Gt, Jt.parser = Gt.parse, Jt.Renderer = Ut, Jt.TextRenderer = Wt, Jt.Lexer = Ht, Jt.lexer = Ht.lex, Jt.Tokenizer = Vt, Jt.Hooks = Kt, Jt.parse = Jt, Jt.options, Jt.setOptions, Jt.use, Jt.walkTokens, Jt.parseInline, Gt.parse, Ht.lex;
//#endregion
//#region node_modules/stylis/src/Enum.js
var Yt = "comm", Xt = "rule", Zt = "decl", Qt = "@import", $t = "@namespace", en = "@keyframes", tn = "@layer", nn = Math.abs, rn = String.fromCharCode;
function an(e) {
	return e.trim();
}
function on(e, t, n) {
	return e.replace(t, n);
}
function sn(e, t) {
	return e.charCodeAt(t) | 0;
}
function cn(e, t, n) {
	return e.slice(t, n);
}
function ln(e) {
	return e.length;
}
function un(e) {
	return e.length;
}
function dn(e, t) {
	return t.push(e), e;
}
//#endregion
//#region node_modules/stylis/src/Tokenizer.js
var fn = 1, pn = 1, mn = 0, hn = 0, gn = 0, _n = "";
function vn(e, t, n, r, i, a, o, s) {
	return {
		value: e,
		root: t,
		parent: n,
		type: r,
		props: i,
		children: a,
		line: fn,
		column: pn,
		length: o,
		return: "",
		siblings: s
	};
}
function yn() {
	return gn;
}
function bn() {
	return gn = hn > 0 ? sn(_n, --hn) : 0, pn--, gn === 10 && (pn = 1, fn--), gn;
}
function xn() {
	return gn = hn < mn ? sn(_n, hn++) : 0, pn++, gn === 10 && (pn = 1, fn++), gn;
}
function Sn() {
	return sn(_n, hn);
}
function Cn() {
	return hn;
}
function wn(e, t) {
	return cn(_n, e, t);
}
function Tn(e) {
	switch (e) {
		case 0:
		case 9:
		case 10:
		case 13:
		case 32: return 5;
		case 33:
		case 43:
		case 44:
		case 47:
		case 62:
		case 64:
		case 126:
		case 59:
		case 123:
		case 125: return 4;
		case 58: return 3;
		case 34:
		case 39:
		case 40:
		case 91: return 2;
		case 41:
		case 93: return 1;
	}
	return 0;
}
function En(e) {
	return fn = pn = 1, mn = ln(_n = e), hn = 0, [];
}
function Dn(e) {
	return _n = "", e;
}
function On(e) {
	return an(wn(hn - 1, jn(e === 91 ? e + 2 : e === 40 ? e + 1 : e)));
}
function kn(e) {
	for (; (gn = Sn()) && gn < 33;) xn();
	return Tn(e) > 2 || Tn(gn) > 3 ? "" : " ";
}
function An(e, t) {
	for (; --t && xn() && !(gn < 48 || gn > 102 || gn > 57 && gn < 65 || gn > 70 && gn < 97););
	return wn(e, Cn() + (t < 6 && Sn() == 32 && xn() == 32));
}
function jn(e) {
	for (; xn();) switch (gn) {
		case e: return hn;
		case 34:
		case 39:
			e !== 34 && e !== 39 && jn(gn);
			break;
		case 40:
			e === 41 && jn(e);
			break;
		case 92:
			xn();
			break;
	}
	return hn;
}
function Mn(e, t) {
	for (; xn() && e + gn !== 57 && !(e + gn === 84 && Sn() === 47););
	return "/*" + wn(t, hn - 1) + "*" + rn(e === 47 ? e : xn());
}
function Nn(e) {
	for (; !Tn(Sn());) xn();
	return wn(e, hn);
}
//#endregion
//#region node_modules/stylis/src/Parser.js
function Pn(e) {
	return Dn(Fn("", null, null, null, [""], e = En(e), 0, [0], e));
}
function Fn(e, t, n, r, i, a, o, s, c) {
	for (var l = 0, u = 0, d = o, f = 0, p = 0, m = 0, h = 1, g = 1, _ = 1, v = 0, y = 0, b = "", x = i, S = a, C = r, w = b; g;) switch (m = y, y = xn()) {
		case 40:
			m != 108 && sn(w, d - 1) == 58 ? (v++, w += "(") : w += On(y);
			break;
		case 41:
			v--, w += ")";
			break;
		case 34:
		case 39:
		case 91:
			w += On(y);
			break;
		case 9:
		case 10:
		case 13:
		case 32:
			if (v > 0) {
				w += rn(y);
				break;
			}
			w += kn(m);
			break;
		case 92:
			w += An(Cn() - 1, 7);
			continue;
		case 47:
			switch (Sn()) {
				case 42:
				case 47:
					dn(Ln(Mn(xn(), Cn()), t, n, c), c), (Tn(m || 1) == 5 || Tn(Sn() || 1) == 5) && ln(w) && cn(w, -1, void 0) !== " " && (w += " ");
					break;
				default: w += "/";
			}
			break;
		case 123 * h: s[l++] = ln(w) * _;
		case 125 * h:
		case 59:
		case 0:
			if (v > 0 && y) {
				w += rn(y);
				break;
			}
			switch (y) {
				case 0:
				case 125: g = 0;
				case 59 + u:
					_ == -1 && (w = on(w, /\f/g, "")), p > 0 && (ln(w) - d || h === 0) && dn(p > 32 ? Rn(w + ";", r, n, d - 1, c) : Rn(on(w, " ", "") + ";", r, n, d - 2, c), c);
					break;
				case 59: w += ";";
				default: if (dn(C = In(w, t, n, l, u, i, s, b, x = [], S = [], d, a), a), y === 123) if (u === 0) Fn(w, t, C, C, x, a, d, s, S);
				else {
					switch (f) {
						case 99: if (sn(w, 3) === 110) break;
						case 108: if (sn(w, 2) === 97) break;
						default: u = 0;
						case 100:
						case 109:
						case 115:
					}
					u ? Fn(e, C, C, r && dn(In(e, C, C, 0, 0, i, s, b, i, x = [], d, S), S), i, S, d, s, r ? x : S) : Fn(w, C, C, C, [""], S, 0, s, S);
				}
			}
			l = u = p = 0, h = _ = 1, b = w = "", d = o;
			break;
		case 58: d = 1 + ln(w), p = m;
		default:
			if (h < 1) {
				if (y == 123) --h;
				else if (y == 125 && h++ == 0 && bn() == 125) continue;
			}
			switch (w += rn(y), y * h) {
				case 38:
					_ = u > 0 ? 1 : (w += "\f", -1);
					break;
				case 44:
					if (v > 0) break;
					s[l++] = (ln(w) - 1) * _, _ = 1;
					break;
				case 64:
					Sn() === 45 && (w += On(xn())), f = Sn(), u = d = ln(b = w += Nn(Cn())), y++;
					break;
				case 45: m === 45 && ln(w) == 2 && (h = 0);
			}
	}
	return a;
}
function In(e, t, n, r, i, a, o, s, c, l, u, d) {
	for (var f = i - 1, p = i === 0 ? a : [""], m = un(p), h = 0, g = 0, _ = 0; h < r; ++h) for (var v = 0, y = cn(e, f + 1, f = nn(g = o[h])), b = e; v < m; ++v) (b = an(g > 0 ? p[v] + " " + y : on(y, /&\f/g, p[v]))) && (c[_++] = b);
	return vn(e, t, n, i === 0 ? Xt : s, c, l, u, d);
}
function Ln(e, t, n, r) {
	return vn(e, t, n, Yt, rn(yn()), cn(e, 2, -2), 0, r);
}
function Rn(e, t, n, r, i) {
	return vn(e, t, n, Zt, cn(e, 0, r), cn(e, r + 1, -1), r, i);
}
//#endregion
//#region node_modules/stylis/src/Serializer.js
function zn(e, t) {
	for (var n = "", r = 0; r < e.length; r++) n += t(e[r], r, e, t) || "";
	return n;
}
function Bn(e, t, n, r) {
	switch (e.type) {
		case tn: if (e.children.length) break;
		case Qt:
		case $t:
		case Zt: return e.return = e.return || e.value;
		case Yt: return "";
		case en: return e.return = e.value + "{" + zn(e.children, r) + "}";
		case Xt: if (!ln(e.value = e.props.join(","))) return "";
	}
	return ln(n = zn(e.children, r)) ? e.return = e.value + "{" + n + "}" : "";
}
//#endregion
//#region node_modules/mermaid/dist/mermaid.core.mjs
var Vn = "c4", Hn = {
	id: Vn,
	detector: /* @__PURE__ */ o((e) => /^\s*C4Context|C4Container|C4Component|C4Dynamic|C4Deployment/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./c4Diagram-YG6GDRKO-DUj9Nrez.js");
		return {
			id: Vn,
			diagram: e
		};
	}, "loader")
}, Un = "flowchart", Wn = {
	id: Un,
	detector: /* @__PURE__ */ o((e, t) => t?.flowchart?.defaultRenderer === "dagre-wrapper" || t?.flowchart?.defaultRenderer === "elk" ? !1 : /^\s*graph/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./flowDiagram-NV44I4VS-CVSbvIN7.js");
		return {
			id: Un,
			diagram: e
		};
	}, "loader")
}, Gn = "flowchart-v2", Kn = {
	id: Gn,
	detector: /* @__PURE__ */ o((e, t) => t?.flowchart?.defaultRenderer === "dagre-d3" ? !1 : (t?.flowchart?.defaultRenderer === "elk" && (t.layout = "elk"), /^\s*graph/.test(e) && t?.flowchart?.defaultRenderer === "dagre-wrapper" ? !0 : /^\s*flowchart/.test(e)), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./flowDiagram-NV44I4VS-CVSbvIN7.js");
		return {
			id: Gn,
			diagram: e
		};
	}, "loader")
}, qn = "er", Jn = {
	id: qn,
	detector: /* @__PURE__ */ o((e) => /^\s*erDiagram/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./erDiagram-Q2GNP2WA-DwKmMoM5.js");
		return {
			id: qn,
			diagram: e
		};
	}, "loader")
}, Yn = "gitGraph", Xn = {
	id: Yn,
	detector: /* @__PURE__ */ o((e) => /^\s*gitGraph/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./gitGraphDiagram-NY62KEGX-CqP1AcKX.js");
		return {
			id: Yn,
			diagram: e
		};
	}, "loader")
}, Zn = "gantt", Qn = {
	id: Zn,
	detector: /* @__PURE__ */ o((e) => /^\s*gantt/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./ganttDiagram-LVOFAZNH-BmqJJ-NL.js");
		return {
			id: Zn,
			diagram: e
		};
	}, "loader")
}, $n = "info", er = {
	id: $n,
	detector: /* @__PURE__ */ o((e) => /^\s*info/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./infoDiagram-F6ZHWCRC-DGRWvZIR.js");
		return {
			id: $n,
			diagram: e
		};
	}, "loader")
}, tr = "pie", nr = {
	id: tr,
	detector: /* @__PURE__ */ o((e) => /^\s*pie/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./pieDiagram-ADFJNKIX-D9cZ-914.js");
		return {
			id: tr,
			diagram: e
		};
	}, "loader")
}, rr = "quadrantChart", ir = {
	id: rr,
	detector: /* @__PURE__ */ o((e) => /^\s*quadrantChart/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./quadrantDiagram-AYHSOK5B-BfWpwEj_.js");
		return {
			id: rr,
			diagram: e
		};
	}, "loader")
}, ar = "xychart", or = {
	id: ar,
	detector: /* @__PURE__ */ o((e) => /^\s*xychart(-beta)?/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./xychartDiagram-PRI3JC2R-D0QW9OM8.js");
		return {
			id: ar,
			diagram: e
		};
	}, "loader")
}, sr = "requirement", cr = {
	id: sr,
	detector: /* @__PURE__ */ o((e) => /^\s*requirement(Diagram)?/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./requirementDiagram-UZGBJVZJ-Bl6Vci1t.js");
		return {
			id: sr,
			diagram: e
		};
	}, "loader")
}, lr = "sequence", ur = {
	id: lr,
	detector: /* @__PURE__ */ o((e) => /^\s*sequenceDiagram/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./sequenceDiagram-WL72ISMW-BfSpOyat.js");
		return {
			id: lr,
			diagram: e
		};
	}, "loader")
}, dr = "class", fr = {
	id: dr,
	detector: /* @__PURE__ */ o((e, t) => t?.class?.defaultRenderer !== "dagre-wrapper" && /^\s*classDiagram/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./classDiagram-2ON5EDUG-BH36Jhev.js");
		return {
			id: dr,
			diagram: e
		};
	}, "loader")
}, pr = "classDiagram", mr = {
	id: pr,
	detector: /* @__PURE__ */ o((e, t) => /^\s*classDiagram/.test(e) && t?.class?.defaultRenderer === "dagre-wrapper" ? !0 : /^\s*classDiagram-v2/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./classDiagram-v2-WZHVMYZB-Bc09K83G.js");
		return {
			id: pr,
			diagram: e
		};
	}, "loader")
}, hr = "state", gr = {
	id: hr,
	detector: /* @__PURE__ */ o((e, t) => t?.state?.defaultRenderer !== "dagre-wrapper" && /^\s*stateDiagram/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./stateDiagram-FKZM4ZOC-B2fLVxpw.js");
		return {
			id: hr,
			diagram: e
		};
	}, "loader")
}, _r = "stateDiagram", vr = {
	id: _r,
	detector: /* @__PURE__ */ o((e, t) => !!(/^\s*stateDiagram-v2/.test(e) || /^\s*stateDiagram/.test(e) && t?.state?.defaultRenderer === "dagre-wrapper"), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./stateDiagram-v2-4FDKWEC3-CYGzacu5.js");
		return {
			id: _r,
			diagram: e
		};
	}, "loader")
}, yr = "journey", br = {
	id: yr,
	detector: /* @__PURE__ */ o((e) => /^\s*journey/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./journeyDiagram-XKPGCS4Q-C444Waq3.js");
		return {
			id: yr,
			diagram: e
		};
	}, "loader")
}, xr = { draw: /* @__PURE__ */ o((e, t, n) => {
	a.debug("rendering svg for syntax error\n");
	let r = ne(t), i = r.append("g");
	r.attr("viewBox", "0 0 2412 512"), _(r, 100, 512, !0), i.append("path").attr("class", "error-icon").attr("d", "m411.313,123.313c6.25-6.25 6.25-16.375 0-22.625s-16.375-6.25-22.625,0l-32,32-9.375,9.375-20.688-20.688c-12.484-12.5-32.766-12.5-45.25,0l-16,16c-1.261,1.261-2.304,2.648-3.31,4.051-21.739-8.561-45.324-13.426-70.065-13.426-105.867,0-192,86.133-192,192s86.133,192 192,192 192-86.133 192-192c0-24.741-4.864-48.327-13.426-70.065 1.402-1.007 2.79-2.049 4.051-3.31l16-16c12.5-12.492 12.5-32.758 0-45.25l-20.688-20.688 9.375-9.375 32.001-31.999zm-219.313,100.687c-52.938,0-96,43.063-96,96 0,8.836-7.164,16-16,16s-16-7.164-16-16c0-70.578 57.422-128 128-128 8.836,0 16,7.164 16,16s-7.164,16-16,16z"), i.append("path").attr("class", "error-icon").attr("d", "m459.02,148.98c-6.25-6.25-16.375-6.25-22.625,0s-6.25,16.375 0,22.625l16,16c3.125,3.125 7.219,4.688 11.313,4.688 4.094,0 8.188-1.563 11.313-4.688 6.25-6.25 6.25-16.375 0-22.625l-16.001-16z"), i.append("path").attr("class", "error-icon").attr("d", "m340.395,75.605c3.125,3.125 7.219,4.688 11.313,4.688 4.094,0 8.188-1.563 11.313-4.688 6.25-6.25 6.25-16.375 0-22.625l-16-16c-6.25-6.25-16.375-6.25-22.625,0s-6.25,16.375 0,22.625l15.999,16z"), i.append("path").attr("class", "error-icon").attr("d", "m400,64c8.844,0 16-7.164 16-16v-32c0-8.836-7.156-16-16-16-8.844,0-16,7.164-16,16v32c0,8.836 7.156,16 16,16z"), i.append("path").attr("class", "error-icon").attr("d", "m496,96.586h-32c-8.844,0-16,7.164-16,16 0,8.836 7.156,16 16,16h32c8.844,0 16-7.164 16-16 0-8.836-7.156-16-16-16z"), i.append("path").attr("class", "error-icon").attr("d", "m436.98,75.605c3.125,3.125 7.219,4.688 11.313,4.688 4.094,0 8.188-1.563 11.313-4.688l32-32c6.25-6.25 6.25-16.375 0-22.625s-16.375-6.25-22.625,0l-32,32c-6.251,6.25-6.251,16.375-0.001,22.625z"), i.append("text").attr("class", "error-text").attr("x", 1440).attr("y", 250).attr("font-size", "150px").style("text-anchor", "middle").text("Syntax error in text"), i.append("text").attr("class", "error-text").attr("x", 1250).attr("y", 400).attr("font-size", "100px").style("text-anchor", "middle").text(`mermaid version ${n}`);
}, "draw") }, Sr = xr, Cr = {
	db: {},
	renderer: xr,
	parser: { parse: /* @__PURE__ */ o(() => {}, "parse") }
}, wr = "flowchart-elk", Tr = {
	id: wr,
	detector: /* @__PURE__ */ o((e, t = {}) => /^\s*flowchart-elk/.test(e) || /^\s*(flowchart|graph)/.test(e) && t?.flowchart?.defaultRenderer === "elk" ? (t.layout = "elk", !0) : !1, "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./flowDiagram-NV44I4VS-CVSbvIN7.js");
		return {
			id: wr,
			diagram: e
		};
	}, "loader")
}, Er = "timeline", Dr = {
	id: Er,
	detector: /* @__PURE__ */ o((e) => /^\s*timeline/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./timeline-definition-IT6M3QCI-HXdkOaN2.js");
		return {
			id: Er,
			diagram: e
		};
	}, "loader")
}, Or = "mindmap", kr = {
	id: Or,
	detector: /* @__PURE__ */ o((e) => /^\s*mindmap/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./mindmap-definition-VGOIOE7T-BNtxI6Wd.js");
		return {
			id: Or,
			diagram: e
		};
	}, "loader")
}, Ar = "kanban", jr = {
	id: Ar,
	detector: /* @__PURE__ */ o((e) => /^\s*kanban/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./kanban-definition-3W4ZIXB7-CXaqcH5p.js");
		return {
			id: Ar,
			diagram: e
		};
	}, "loader")
}, Mr = "sankey", Nr = {
	id: Mr,
	detector: /* @__PURE__ */ o((e) => /^\s*sankey(-beta)?/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./sankeyDiagram-TZEHDZUN-DRBtADa9.js");
		return {
			id: Mr,
			diagram: e
		};
	}, "loader")
}, Pr = "packet", Fr = {
	id: Pr,
	detector: /* @__PURE__ */ o((e) => /^\s*packet(-beta)?/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./diagram-S2PKOQOG-B0lfZoPs.js");
		return {
			id: Pr,
			diagram: e
		};
	}, "loader")
}, Ir = "radar", Lr = {
	id: Ir,
	detector: /* @__PURE__ */ o((e) => /^\s*radar-beta/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./diagram-QEK2KX5R-DG2HuV0w.js");
		return {
			id: Ir,
			diagram: e
		};
	}, "loader")
}, Rr = "block", zr = {
	id: Rr,
	detector: /* @__PURE__ */ o((e) => /^\s*block(-beta)?/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./blockDiagram-VD42YOAC-CmCUkqCD.js");
		return {
			id: Rr,
			diagram: e
		};
	}, "loader")
}, Br = "architecture", Vr = {
	id: Br,
	detector: /* @__PURE__ */ o((e) => /^\s*architecture/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./architectureDiagram-VXUJARFQ-BSmNNANw.js");
		return {
			id: Br,
			diagram: e
		};
	}, "loader")
}, Hr = "treemap", Ur = {
	id: Hr,
	detector: /* @__PURE__ */ o((e) => /^\s*treemap/.test(e), "detector"),
	loader: /* @__PURE__ */ o(async () => {
		let { diagram: e } = await import("./diagram-PSM6KHXK-CbLtQDqp.js");
		return {
			id: Hr,
			diagram: e
		};
	}, "loader")
}, Wr = !1, Gr = /* @__PURE__ */ o(() => {
	Wr || (Wr = !0, x("error", Cr, (e) => e.toLowerCase().trim() === "error"), x("---", {
		db: { clear: /* @__PURE__ */ o(() => {}, "clear") },
		styles: {},
		renderer: { draw: /* @__PURE__ */ o(() => {}, "draw") },
		parser: { parse: /* @__PURE__ */ o(() => {
			throw Error("Diagrams beginning with --- are not valid. If you were trying to use a YAML front-matter, please ensure that you've correctly opened and closed the YAML front-matter with un-indented `---` blocks");
		}, "parse") },
		init: /* @__PURE__ */ o(() => null, "init")
	}, (e) => e.toLowerCase().trimStart().startsWith("---")), l(Tr, kr, Vr), l(Hn, jr, mr, fr, Jn, Qn, er, nr, cr, ur, Kn, Wn, Dr, Xn, vr, gr, br, ir, Nr, Fr, or, zr, Lr, Ur));
}, "addDiagrams"), Kr = /* @__PURE__ */ o(async () => {
	a.debug("Loading registered diagrams");
	let e = (await Promise.allSettled(Object.entries(w).map(async ([e, { detector: t, loader: n }]) => {
		if (n) try {
			k(e);
		} catch {
			try {
				let { diagram: e, id: r } = await n();
				x(r, e, t);
			} catch (t) {
				throw a.error(`Failed to load external diagram with key ${e}. Removing from detectors.`), delete w[e], t;
			}
		}
	}))).filter((e) => e.status === "rejected");
	if (e.length > 0) {
		a.error(`Failed to load ${e.length} external diagrams`);
		for (let t of e) a.error(t);
		throw Error(`Failed to load ${e.length} external diagrams`);
	}
}, "loadRegisteredDiagrams"), qr = "graphics-document document";
function Jr(e, t) {
	e.attr("role", qr), t !== "" && e.attr("aria-roledescription", t);
}
o(Jr, "setA11yDiagramInfo");
function Yr(e, t, n, r) {
	if (e.insert !== void 0) {
		if (n) {
			let t = `chart-desc-${r}`;
			e.attr("aria-describedby", t), e.insert("desc", ":first-child").attr("id", t).text(n);
		}
		if (t) {
			let n = `chart-title-${r}`;
			e.attr("aria-labelledby", n), e.insert("title", ":first-child").attr("id", n).text(t);
		}
	}
}
o(Yr, "addSVGa11yTitleDescription");
var Xr = class e {
	constructor(e, t, n, r, i) {
		this.type = e, this.text = t, this.db = n, this.parser = r, this.renderer = i;
	}
	static {
		o(this, "Diagram");
	}
	static async fromText(t, n = {}) {
		let r = ee(), i = v(t, r);
		t = A(t) + "\n";
		try {
			k(i);
		} catch {
			let e = f(i);
			if (!e) throw new D(`Diagram ${i} not found.`);
			let { id: t, diagram: n } = await e();
			x(t, n);
		}
		let { db: a, parser: o, renderer: s, init: c } = k(i);
		return o.parser && (o.parser.yy = a), a.clear?.(), c?.(r), n.title && a.setDiagramTitle?.(n.title), await o.parse(t), new e(i, t, a, o, s);
	}
	async render(e, t) {
		await this.renderer.draw(this.text, e, t, this);
	}
	getParser() {
		return this.parser;
	}
	getType() {
		return this.type;
	}
}, Zr = [], Qr = /* @__PURE__ */ o(() => {
	Zr.forEach((e) => {
		e();
	}), Zr = [];
}, "attachFunctions"), $r = /* @__PURE__ */ o((e) => e.replace(/^\s*%%(?!{)[^\n]+\n?/gm, "").trimStart(), "cleanupComments");
function ei(e) {
	let t = e.match(y);
	if (!t) return {
		text: e,
		metadata: {}
	};
	let n = re(t[1], { schema: ie }) ?? {};
	n = typeof n == "object" && !Array.isArray(n) ? n : {};
	let r = {};
	return n.displayMode && (r.displayMode = n.displayMode.toString()), n.title && (r.title = n.title.toString()), n.config && (r.config = n.config), {
		text: e.slice(t[0].length),
		metadata: r
	};
}
o(ei, "extractFrontMatter");
var ti = /* @__PURE__ */ o((e) => e.replace(/\r\n?/g, "\n").replace(/<(\w+)([^>]*)>/g, (e, t, n) => "<" + t + n.replace(/="([^"]*)"/g, "='$1'") + ">"), "cleanupText"), ni = /* @__PURE__ */ o((e) => {
	let { text: t, metadata: n } = ei(e), { displayMode: r, title: i, config: a = {} } = n;
	return r && (a.gantt ||= {}, a.gantt.displayMode = r), {
		title: i,
		config: a,
		text: t
	};
}, "processFrontmatter"), ri = /* @__PURE__ */ o((e) => {
	let t = M.detectInit(e) ?? {}, n = M.detectDirective(e, "wrap");
	return Array.isArray(n) ? t.wrap = n.some(({ type: e }) => e === "wrap") : n?.type === "wrap" && (t.wrap = !0), {
		text: P(e),
		directive: t
	};
}, "processDirectives");
function ii(e) {
	let t = ni(ti(e)), n = ri(t.text), r = te(t.config, n.directive);
	return e = $r(n.text), {
		code: e,
		title: t.title,
		config: r
	};
}
o(ii, "preprocessDiagram");
function ai(e) {
	let t = new TextEncoder().encode(e), n = Array.from(t, (e) => String.fromCodePoint(e)).join("");
	return btoa(n);
}
o(ai, "toBase64");
var oi = 5e4, si = "graph TB;a[Maximum text size in diagram exceeded];style a fill:#faa", ci = "sandbox", li = "loose", ui = "http://www.w3.org/2000/svg", di = "http://www.w3.org/1999/xlink", fi = "http://www.w3.org/1999/xhtml", pi = "100%", mi = "100%", hi = "border:0;margin:0;", gi = "margin:0", _i = "allow-top-navigation-by-user-activation allow-popups", vi = "The \"iframe\" tag is not supported by your browser.", yi = ["foreignobject"], bi = ["dominant-baseline"];
function xi(e) {
	let t = ii(e);
	return u(), C(t.config ?? {}), t;
}
o(xi, "processAndSetConfigs");
async function Si(e, t) {
	Gr();
	try {
		let { code: t, config: n } = xi(e);
		return {
			diagramType: (await Ni(t)).type,
			config: n
		};
	} catch (e) {
		if (t?.suppressErrors) return !1;
		throw e;
	}
}
o(Si, "parse");
var Ci = /* @__PURE__ */ o((e, t, n = []) => `
.${e} ${t} { ${n.join(" !important; ")} !important; }`, "cssImportantStyles"), wi = /* @__PURE__ */ o((e, t = /* @__PURE__ */ new Map()) => {
	let n = "";
	if (e.themeCSS !== void 0 && (n += `
${e.themeCSS}`), e.fontFamily !== void 0 && (n += `
:root { --mermaid-font-family: ${e.fontFamily}}`), e.altFontFamily !== void 0 && (n += `
:root { --mermaid-alt-font-family: ${e.altFontFamily}}`), t instanceof Map) {
		let r = e.htmlLabels ?? e.flowchart?.htmlLabels ? ["> *", "span"] : [
			"rect",
			"polygon",
			"ellipse",
			"circle",
			"path"
		];
		t.forEach((e) => {
			se(e.styles) || r.forEach((t) => {
				n += Ci(e.id, t, e.styles);
			}), se(e.textStyles) || (n += Ci(e.id, "tspan", (e?.textStyles || []).map((e) => e.replace("color", "fill"))));
		});
	}
	return n;
}, "createCssStyles"), Ti = /* @__PURE__ */ o((e, t, n, r) => zn(Pn(`${r}{${T(t, wi(e, n), e.themeVariables)}}`), Bn), "createUserStyles"), Ei = /* @__PURE__ */ o((e = "", t, n) => {
	let r = e;
	return !n && !t && (r = r.replace(/marker-end="url\([\d+./:=?A-Za-z-]*?#/g, "marker-end=\"url(#")), r = N(r), r = r.replace(/<br>/g, "<br/>"), r;
}, "cleanUpSvgCode"), Di = /* @__PURE__ */ o((e = "", t) => `<iframe style="width:${pi};height:${t?.viewBox?.baseVal?.height ? t.viewBox.baseVal.height + "px" : mi};${hi}" src="data:text/html;charset=UTF-8;base64,${ai(`<body style="${gi}">${e}</body>`)}" sandbox="${_i}">
  ${vi}
</iframe>`, "putIntoIFrame"), Oi = /* @__PURE__ */ o((e, t, n, r, i) => {
	let a = e.append("div");
	a.attr("id", n), r && a.attr("style", r);
	let o = a.append("svg").attr("id", t).attr("width", "100%").attr("xmlns", ui);
	return i && o.attr("xmlns:xlink", i), o.append("g"), e;
}, "appendDivSvgG");
function ki(e, t) {
	return e.append("iframe").attr("id", t).attr("style", "width: 100%; height: 100%;").attr("sandbox", "");
}
o(ki, "sandboxedIframe");
var Ai = /* @__PURE__ */ o((e, t, n, r) => {
	e.getElementById(t)?.remove(), e.getElementById(n)?.remove(), e.getElementById(r)?.remove();
}, "removeExistingElements"), ji = /* @__PURE__ */ o(async function(e, t, n) {
	Gr();
	let i = xi(t);
	t = i.code;
	let c = ee();
	a.debug(c), t.length > (c?.maxTextSize ?? oi) && (t = si);
	let l = "#" + e, u = "i" + e, d = "#" + u, f = "d" + e, p = "#" + f, m = /* @__PURE__ */ o(() => {
		let e = s(_ ? d : p).node();
		e && "remove" in e && e.remove();
	}, "removeTempElements"), g = s("body"), _ = c.securityLevel === ci, v = c.securityLevel === li, y = c.fontFamily;
	n === void 0 ? (Ai(document, e, f, u), _ ? (g = s(ki(s("body"), u).nodes()[0].contentDocument.body), g.node().style.margin = 0) : g = s("body"), Oi(g, e, f)) : (n && (n.innerHTML = ""), _ ? (g = s(ki(s(n), u).nodes()[0].contentDocument.body), g.node().style.margin = 0) : g = s(n), Oi(g, e, f, `font-family: ${y}`, di));
	let x, S;
	try {
		x = await Xr.fromText(t, { title: i.title });
	} catch (e) {
		if (c.suppressErrorRendering) throw m(), e;
		x = await Xr.fromText("error"), S = e;
	}
	let C = g.select(p).node(), w = x.type, T = C.firstChild, E = T.firstChild, D = x.renderer.getClasses?.(t, x), O = Ti(c, w, D, l), k = document.createElement("style");
	k.innerHTML = O, T.insertBefore(k, E);
	try {
		await x.renderer.draw(t, e, r.version, x);
	} catch (n) {
		throw c.suppressErrorRendering ? m() : Sr.draw(t, e, r.version), n;
	}
	let A = g.select(`${p} svg`), j = x.db.getAccTitle?.(), M = x.db.getAccDescription?.();
	Pi(w, A, j, M), g.select(`[id="${e}"]`).selectAll("foreignobject > *").attr("xmlns", fi);
	let N = g.select(p).node().innerHTML;
	if (a.debug("config.arrowMarkerAbsolute", c.arrowMarkerAbsolute), N = Ei(N, _, b(c.arrowMarkerAbsolute)), _) {
		let e = g.select(p + " svg").node();
		N = Di(N, e);
	} else v || (N = h.sanitize(N, {
		ADD_TAGS: yi,
		ADD_ATTR: bi,
		HTML_INTEGRATION_POINTS: { foreignobject: !0 }
	}));
	if (Qr(), S) throw S;
	return m(), {
		diagramType: w,
		svg: N,
		bindFunctions: x.db.bindFunctions
	};
}, "render");
function Mi(e = {}) {
	let t = E({}, e);
	t?.fontFamily && !t.themeVariables?.fontFamily && (t.themeVariables ||= {}, t.themeVariables.fontFamily = t.fontFamily), d(t), t?.theme && t.theme in c ? t.themeVariables = c[t.theme].getThemeVariables(t.themeVariables) : t && (t.themeVariables = c.default.getThemeVariables(t.themeVariables)), i((typeof t == "object" ? m(t) : O()).logLevel), Gr();
}
o(Mi, "initialize");
var Ni = /* @__PURE__ */ o((e, t = {}) => {
	let { code: n } = ii(e);
	return Xr.fromText(n, t);
}, "getDiagramFromText");
function Pi(e, t, n, r) {
	Jr(t, e), Yr(t, n, r, t.attr("id"));
}
o(Pi, "addA11yInfo");
var z = Object.freeze({
	render: ji,
	parse: Si,
	getDiagramFromText: Ni,
	initialize: Mi,
	getConfig: ee,
	setConfig: p,
	getSiteConfig: O,
	updateSiteConfig: g,
	reset: /* @__PURE__ */ o(() => {
		u();
	}, "reset"),
	globalReset: /* @__PURE__ */ o(() => {
		u(S);
	}, "globalReset"),
	defaultConfig: S
});
i(ee().logLevel), u(ee());
var Fi = /* @__PURE__ */ o((e, t, n) => {
	a.warn(e), j(e) ? (n && n(e.str, e.hash), t.push({
		...e,
		message: e.str,
		error: e
	})) : (n && n(e), e instanceof Error && t.push({
		str: e.message,
		message: e.message,
		hash: e.name,
		error: e
	}));
}, "handleError"), Ii = /* @__PURE__ */ o(async function(e = { querySelector: ".mermaid" }) {
	try {
		await Li(e);
	} catch (t) {
		if (j(t) && a.error(t.str), Ji.parseError && Ji.parseError(t), !e.suppressErrors) throw a.error("Use the suppressErrors option to suppress these errors"), t;
	}
}, "run"), Li = /* @__PURE__ */ o(async function({ postRenderCallback: e, querySelector: t, nodes: n } = { querySelector: ".mermaid" }) {
	let r = z.getConfig();
	a.debug(`${e ? "" : "No "}Callback function found`);
	let i;
	if (n) i = n;
	else if (t) i = document.querySelectorAll(t);
	else throw Error("Nodes and querySelector are both undefined");
	a.debug(`Found ${i.length} diagrams`), r?.startOnLoad !== void 0 && (a.debug("Start On Load: " + r?.startOnLoad), z.updateSiteConfig({ startOnLoad: r?.startOnLoad }));
	let o = new M.InitIDGenerator(r.deterministicIds, r.deterministicIDSeed), s, c = [];
	for (let t of Array.from(i)) {
		if (a.info("Rendering diagram: " + t.id), t.getAttribute("data-processed")) continue;
		t.setAttribute("data-processed", "true");
		let n = `mermaid-${o.next()}`;
		s = t.innerHTML, s = ae(M.entityDecode(s)).trim().replace(/<br\s*\/?>/gi, "<br/>");
		let r = M.detectInit(s);
		r && a.debug("Detected early reinit: ", r);
		try {
			let { svg: r, bindFunctions: i } = await qi(n, s, t);
			t.innerHTML = r, e && await e(n), i && i(t);
		} catch (e) {
			Fi(e, c, Ji.parseError);
		}
	}
	if (c.length > 0) throw c[0];
}, "runThrowsErrors"), Ri = /* @__PURE__ */ o(function(e) {
	z.initialize(e);
}, "initialize"), zi = /* @__PURE__ */ o(async function(e, t, n) {
	a.warn("mermaid.init is deprecated. Please use run instead."), e && Ri(e);
	let r = {
		postRenderCallback: n,
		querySelector: ".mermaid"
	};
	typeof t == "string" ? r.querySelector = t : t && (t instanceof HTMLElement ? r.nodes = [t] : r.nodes = t), await Ii(r);
}, "init"), Bi = /* @__PURE__ */ o(async (e, { lazyLoad: t = !0 } = {}) => {
	Gr(), l(...e), t === !1 && await Kr();
}, "registerExternalDiagrams"), Vi = /* @__PURE__ */ o(function() {
	if (Ji.startOnLoad) {
		let { startOnLoad: e } = z.getConfig();
		e && Ji.run().catch((e) => a.error("Mermaid failed to initialize", e));
	}
}, "contentLoaded");
typeof document < "u" && window.addEventListener("load", Vi, !1);
var Hi = /* @__PURE__ */ o(function(e) {
	Ji.parseError = e;
}, "setParseErrorHandler"), Ui = [], Wi = !1, Gi = /* @__PURE__ */ o(async () => {
	if (!Wi) {
		for (Wi = !0; Ui.length > 0;) {
			let e = Ui.shift();
			if (e) try {
				await e();
			} catch (e) {
				a.error("Error executing queue", e);
			}
		}
		Wi = !1;
	}
}, "executeQueue"), Ki = /* @__PURE__ */ o(async (e, t) => new Promise((n, r) => {
	let i = /* @__PURE__ */ o(() => new Promise((i, o) => {
		z.parse(e, t).then((e) => {
			i(e), n(e);
		}, (e) => {
			a.error("Error parsing", e), Ji.parseError?.(e), o(e), r(e);
		});
	}), "performCall");
	Ui.push(i), Gi().catch(r);
}), "parse"), qi = /* @__PURE__ */ o((e, t, n) => new Promise((r, i) => {
	let s = /* @__PURE__ */ o(() => new Promise((o, s) => {
		z.render(e, t, n).then((e) => {
			o(e), r(e);
		}, (e) => {
			a.error("Error parsing", e), Ji.parseError?.(e), s(e), i(e);
		});
	}), "performCall");
	Ui.push(s), Gi().catch(i);
}), "render"), Ji = {
	startOnLoad: !0,
	mermaidAPI: z,
	parse: Ki,
	render: qi,
	init: zi,
	run: Ii,
	registerExternalDiagrams: Bi,
	registerLayoutLoaders: oe,
	initialize: Ri,
	parseError: void 0,
	contentLoaded: Vi,
	setParseErrorHandler: Hi,
	detectType: v,
	registerIconPacks: F,
	getRegisteredDiagramsMetadata: /* @__PURE__ */ o(() => Object.keys(w).map((e) => ({ id: e })), "getRegisteredDiagramsMetadata")
}, Yi = Ji;
//#endregion
//#region node_modules/comma-separated-tokens/index.js
function Xi(e, t) {
	let n = t || {};
	return (e[e.length - 1] === "" ? [...e, ""] : e).join((n.padRight ? " " : "") + "," + (n.padLeft === !1 ? "" : " ")).trim();
}
//#endregion
//#region node_modules/estree-util-is-identifier-name/lib/index.js
var Zi = /^[$_\p{ID_Start}][$_\u{200C}\u{200D}\p{ID_Continue}]*$/u, Qi = /^[$_\p{ID_Start}][-$_\u{200C}\u{200D}\p{ID_Continue}]*$/u, $i = {};
function ea(e, t) {
	return ((t || $i).jsx ? Qi : Zi).test(e);
}
//#endregion
//#region node_modules/hast-util-whitespace/lib/index.js
var ta = /[ \t\n\f\r]/g;
function na(e) {
	return typeof e == "object" ? e.type === "text" && ra(e.value) : ra(e);
}
function ra(e) {
	return e.replace(ta, "") === "";
}
//#endregion
//#region node_modules/property-information/lib/util/schema.js
var ia = class {
	constructor(e, t, n) {
		this.normal = t, this.property = e, n && (this.space = n);
	}
};
ia.prototype.normal = {}, ia.prototype.property = {}, ia.prototype.space = void 0;
//#endregion
//#region node_modules/property-information/lib/util/merge.js
function aa(e, t) {
	let n = {}, r = {};
	for (let t of e) Object.assign(n, t.property), Object.assign(r, t.normal);
	return new ia(n, r, t);
}
//#endregion
//#region node_modules/property-information/lib/normalize.js
function oa(e) {
	return e.toLowerCase();
}
//#endregion
//#region node_modules/property-information/lib/util/info.js
var sa = class {
	constructor(e, t) {
		this.attribute = t, this.property = e;
	}
};
sa.prototype.attribute = "", sa.prototype.booleanish = !1, sa.prototype.boolean = !1, sa.prototype.commaOrSpaceSeparated = !1, sa.prototype.commaSeparated = !1, sa.prototype.defined = !1, sa.prototype.mustUseProperty = !1, sa.prototype.number = !1, sa.prototype.overloadedBoolean = !1, sa.prototype.property = "", sa.prototype.spaceSeparated = !1, sa.prototype.space = void 0;
//#endregion
//#region node_modules/property-information/lib/util/types.js
var ca = /* @__PURE__ */ t({
	boolean: () => B,
	booleanish: () => ua,
	commaOrSpaceSeparated: () => ma,
	commaSeparated: () => pa,
	number: () => V,
	overloadedBoolean: () => da,
	spaceSeparated: () => fa
}), la = 0, B = ha(), ua = ha(), da = ha(), V = ha(), fa = ha(), pa = ha(), ma = ha();
function ha() {
	return 2 ** ++la;
}
//#endregion
//#region node_modules/property-information/lib/util/defined-info.js
var ga = Object.keys(ca), _a = class extends sa {
	constructor(e, t, n, r) {
		let i = -1;
		if (super(e, t), va(this, "space", r), typeof n == "number") for (; ++i < ga.length;) {
			let e = ga[i];
			va(this, ga[i], (n & ca[e]) === ca[e]);
		}
	}
};
_a.prototype.defined = !0;
function va(e, t, n) {
	n && (e[t] = n);
}
//#endregion
//#region node_modules/property-information/lib/util/create.js
function ya(e) {
	let t = {}, n = {};
	for (let [r, i] of Object.entries(e.properties)) {
		let a = new _a(r, e.transform(e.attributes || {}, r), i, e.space);
		e.mustUseProperty && e.mustUseProperty.includes(r) && (a.mustUseProperty = !0), t[r] = a, n[oa(r)] = r, n[oa(a.attribute)] = r;
	}
	return new ia(t, n, e.space);
}
//#endregion
//#region node_modules/property-information/lib/aria.js
var ba = ya({
	properties: {
		ariaActiveDescendant: null,
		ariaAtomic: ua,
		ariaAutoComplete: null,
		ariaBusy: ua,
		ariaChecked: ua,
		ariaColCount: V,
		ariaColIndex: V,
		ariaColSpan: V,
		ariaControls: fa,
		ariaCurrent: null,
		ariaDescribedBy: fa,
		ariaDetails: null,
		ariaDisabled: ua,
		ariaDropEffect: fa,
		ariaErrorMessage: null,
		ariaExpanded: ua,
		ariaFlowTo: fa,
		ariaGrabbed: ua,
		ariaHasPopup: null,
		ariaHidden: ua,
		ariaInvalid: null,
		ariaKeyShortcuts: null,
		ariaLabel: null,
		ariaLabelledBy: fa,
		ariaLevel: V,
		ariaLive: null,
		ariaModal: ua,
		ariaMultiLine: ua,
		ariaMultiSelectable: ua,
		ariaOrientation: null,
		ariaOwns: fa,
		ariaPlaceholder: null,
		ariaPosInSet: V,
		ariaPressed: ua,
		ariaReadOnly: ua,
		ariaRelevant: null,
		ariaRequired: ua,
		ariaRoleDescription: fa,
		ariaRowCount: V,
		ariaRowIndex: V,
		ariaRowSpan: V,
		ariaSelected: ua,
		ariaSetSize: V,
		ariaSort: null,
		ariaValueMax: V,
		ariaValueMin: V,
		ariaValueNow: V,
		ariaValueText: null,
		role: null
	},
	transform(e, t) {
		return t === "role" ? t : "aria-" + t.slice(4).toLowerCase();
	}
});
//#endregion
//#region node_modules/property-information/lib/util/case-sensitive-transform.js
function xa(e, t) {
	return t in e ? e[t] : t;
}
//#endregion
//#region node_modules/property-information/lib/util/case-insensitive-transform.js
function Sa(e, t) {
	return xa(e, t.toLowerCase());
}
//#endregion
//#region node_modules/property-information/lib/html.js
var Ca = ya({
	attributes: {
		acceptcharset: "accept-charset",
		classname: "class",
		htmlfor: "for",
		httpequiv: "http-equiv"
	},
	mustUseProperty: [
		"checked",
		"multiple",
		"muted",
		"selected"
	],
	properties: {
		abbr: null,
		accept: pa,
		acceptCharset: fa,
		accessKey: fa,
		action: null,
		allow: null,
		allowFullScreen: B,
		allowPaymentRequest: B,
		allowUserMedia: B,
		alpha: B,
		alt: null,
		as: null,
		async: B,
		autoCapitalize: null,
		autoComplete: fa,
		autoFocus: B,
		autoPlay: B,
		blocking: fa,
		capture: null,
		charSet: null,
		checked: B,
		cite: null,
		className: fa,
		closedBy: null,
		colorSpace: null,
		cols: V,
		colSpan: V,
		command: null,
		commandFor: null,
		content: null,
		contentEditable: ua,
		controls: B,
		controlsList: fa,
		coords: V | pa,
		crossOrigin: null,
		data: null,
		dateTime: null,
		decoding: null,
		default: B,
		defer: B,
		dir: null,
		dirName: null,
		disabled: B,
		download: da,
		draggable: ua,
		encType: null,
		enterKeyHint: null,
		fetchPriority: null,
		form: null,
		formAction: null,
		formEncType: null,
		formMethod: null,
		formNoValidate: B,
		formTarget: null,
		headers: fa,
		height: V,
		hidden: da,
		high: V,
		href: null,
		hrefLang: null,
		htmlFor: fa,
		httpEquiv: fa,
		id: null,
		imageSizes: null,
		imageSrcSet: null,
		inert: B,
		inputMode: null,
		integrity: null,
		is: null,
		isMap: B,
		itemId: null,
		itemProp: fa,
		itemRef: fa,
		itemScope: B,
		itemType: fa,
		kind: null,
		label: null,
		lang: null,
		language: null,
		list: null,
		loading: null,
		loop: B,
		low: V,
		manifest: null,
		max: null,
		maxLength: V,
		media: null,
		method: null,
		min: null,
		minLength: V,
		multiple: B,
		muted: B,
		name: null,
		nonce: null,
		noModule: B,
		noValidate: B,
		onAbort: null,
		onAfterPrint: null,
		onAuxClick: null,
		onBeforeMatch: null,
		onBeforePrint: null,
		onBeforeToggle: null,
		onBeforeUnload: null,
		onBlur: null,
		onCancel: null,
		onCanPlay: null,
		onCanPlayThrough: null,
		onChange: null,
		onClick: null,
		onClose: null,
		onContextLost: null,
		onContextMenu: null,
		onContextRestored: null,
		onCopy: null,
		onCueChange: null,
		onCut: null,
		onDblClick: null,
		onDrag: null,
		onDragEnd: null,
		onDragEnter: null,
		onDragExit: null,
		onDragLeave: null,
		onDragOver: null,
		onDragStart: null,
		onDrop: null,
		onDurationChange: null,
		onEmptied: null,
		onEnded: null,
		onError: null,
		onFocus: null,
		onFormData: null,
		onHashChange: null,
		onInput: null,
		onInvalid: null,
		onKeyDown: null,
		onKeyPress: null,
		onKeyUp: null,
		onLanguageChange: null,
		onLoad: null,
		onLoadedData: null,
		onLoadedMetadata: null,
		onLoadEnd: null,
		onLoadStart: null,
		onMessage: null,
		onMessageError: null,
		onMouseDown: null,
		onMouseEnter: null,
		onMouseLeave: null,
		onMouseMove: null,
		onMouseOut: null,
		onMouseOver: null,
		onMouseUp: null,
		onOffline: null,
		onOnline: null,
		onPageHide: null,
		onPageShow: null,
		onPaste: null,
		onPause: null,
		onPlay: null,
		onPlaying: null,
		onPopState: null,
		onProgress: null,
		onRateChange: null,
		onRejectionHandled: null,
		onReset: null,
		onResize: null,
		onScroll: null,
		onScrollEnd: null,
		onSecurityPolicyViolation: null,
		onSeeked: null,
		onSeeking: null,
		onSelect: null,
		onSlotChange: null,
		onStalled: null,
		onStorage: null,
		onSubmit: null,
		onSuspend: null,
		onTimeUpdate: null,
		onToggle: null,
		onUnhandledRejection: null,
		onUnload: null,
		onVolumeChange: null,
		onWaiting: null,
		onWheel: null,
		open: B,
		optimum: V,
		pattern: null,
		ping: fa,
		placeholder: null,
		playsInline: B,
		popover: null,
		popoverTarget: null,
		popoverTargetAction: null,
		poster: null,
		preload: null,
		readOnly: B,
		referrerPolicy: null,
		rel: fa,
		required: B,
		reversed: B,
		rows: V,
		rowSpan: V,
		sandbox: fa,
		scope: null,
		scoped: B,
		seamless: B,
		selected: B,
		shadowRootClonable: B,
		shadowRootCustomElementRegistry: B,
		shadowRootDelegatesFocus: B,
		shadowRootMode: null,
		shadowRootSerializable: B,
		shape: null,
		size: V,
		sizes: null,
		slot: null,
		span: V,
		spellCheck: ua,
		src: null,
		srcDoc: null,
		srcLang: null,
		srcSet: null,
		start: V,
		step: null,
		style: null,
		tabIndex: V,
		target: null,
		title: null,
		translate: null,
		type: null,
		typeMustMatch: B,
		useMap: null,
		value: ua,
		width: V,
		wrap: null,
		writingSuggestions: null,
		align: null,
		aLink: null,
		archive: fa,
		axis: null,
		background: null,
		bgColor: null,
		border: V,
		borderColor: null,
		bottomMargin: V,
		cellPadding: null,
		cellSpacing: null,
		char: null,
		charOff: null,
		classId: null,
		clear: null,
		code: null,
		codeBase: null,
		codeType: null,
		color: null,
		compact: B,
		declare: B,
		event: null,
		face: null,
		frame: null,
		frameBorder: null,
		hSpace: V,
		leftMargin: V,
		link: null,
		longDesc: null,
		lowSrc: null,
		marginHeight: V,
		marginWidth: V,
		noResize: B,
		noHref: B,
		noShade: B,
		noWrap: B,
		object: null,
		profile: null,
		prompt: null,
		rev: null,
		rightMargin: V,
		rules: null,
		scheme: null,
		scrolling: ua,
		standby: null,
		summary: null,
		text: null,
		topMargin: V,
		valueType: null,
		version: null,
		vAlign: null,
		vLink: null,
		vSpace: V,
		allowTransparency: null,
		autoCorrect: null,
		autoSave: null,
		credentialless: B,
		disablePictureInPicture: B,
		disableRemotePlayback: B,
		exportParts: pa,
		part: fa,
		prefix: null,
		property: null,
		results: V,
		security: null,
		unselectable: null
	},
	space: "html",
	transform: Sa
}), wa = ya({
	attributes: {
		accentHeight: "accent-height",
		alignmentBaseline: "alignment-baseline",
		arabicForm: "arabic-form",
		baselineShift: "baseline-shift",
		capHeight: "cap-height",
		className: "class",
		clipPath: "clip-path",
		clipRule: "clip-rule",
		colorInterpolation: "color-interpolation",
		colorInterpolationFilters: "color-interpolation-filters",
		colorProfile: "color-profile",
		colorRendering: "color-rendering",
		crossOrigin: "crossorigin",
		dataType: "datatype",
		dominantBaseline: "dominant-baseline",
		enableBackground: "enable-background",
		fillOpacity: "fill-opacity",
		fillRule: "fill-rule",
		floodColor: "flood-color",
		floodOpacity: "flood-opacity",
		fontFamily: "font-family",
		fontSize: "font-size",
		fontSizeAdjust: "font-size-adjust",
		fontStretch: "font-stretch",
		fontStyle: "font-style",
		fontVariant: "font-variant",
		fontWeight: "font-weight",
		glyphName: "glyph-name",
		glyphOrientationHorizontal: "glyph-orientation-horizontal",
		glyphOrientationVertical: "glyph-orientation-vertical",
		hrefLang: "hreflang",
		horizAdvX: "horiz-adv-x",
		horizOriginX: "horiz-origin-x",
		horizOriginY: "horiz-origin-y",
		imageRendering: "image-rendering",
		letterSpacing: "letter-spacing",
		lightingColor: "lighting-color",
		markerEnd: "marker-end",
		markerMid: "marker-mid",
		markerStart: "marker-start",
		maskType: "mask-type",
		navDown: "nav-down",
		navDownLeft: "nav-down-left",
		navDownRight: "nav-down-right",
		navLeft: "nav-left",
		navNext: "nav-next",
		navPrev: "nav-prev",
		navRight: "nav-right",
		navUp: "nav-up",
		navUpLeft: "nav-up-left",
		navUpRight: "nav-up-right",
		onAbort: "onabort",
		onActivate: "onactivate",
		onAfterPrint: "onafterprint",
		onBeforePrint: "onbeforeprint",
		onBegin: "onbegin",
		onCancel: "oncancel",
		onCanPlay: "oncanplay",
		onCanPlayThrough: "oncanplaythrough",
		onChange: "onchange",
		onClick: "onclick",
		onClose: "onclose",
		onCopy: "oncopy",
		onCueChange: "oncuechange",
		onCut: "oncut",
		onDblClick: "ondblclick",
		onDrag: "ondrag",
		onDragEnd: "ondragend",
		onDragEnter: "ondragenter",
		onDragExit: "ondragexit",
		onDragLeave: "ondragleave",
		onDragOver: "ondragover",
		onDragStart: "ondragstart",
		onDrop: "ondrop",
		onDurationChange: "ondurationchange",
		onEmptied: "onemptied",
		onEnd: "onend",
		onEnded: "onended",
		onError: "onerror",
		onFocus: "onfocus",
		onFocusIn: "onfocusin",
		onFocusOut: "onfocusout",
		onHashChange: "onhashchange",
		onInput: "oninput",
		onInvalid: "oninvalid",
		onKeyDown: "onkeydown",
		onKeyPress: "onkeypress",
		onKeyUp: "onkeyup",
		onLoad: "onload",
		onLoadedData: "onloadeddata",
		onLoadedMetadata: "onloadedmetadata",
		onLoadStart: "onloadstart",
		onMessage: "onmessage",
		onMouseDown: "onmousedown",
		onMouseEnter: "onmouseenter",
		onMouseLeave: "onmouseleave",
		onMouseMove: "onmousemove",
		onMouseOut: "onmouseout",
		onMouseOver: "onmouseover",
		onMouseUp: "onmouseup",
		onMouseWheel: "onmousewheel",
		onOffline: "onoffline",
		onOnline: "ononline",
		onPageHide: "onpagehide",
		onPageShow: "onpageshow",
		onPaste: "onpaste",
		onPause: "onpause",
		onPlay: "onplay",
		onPlaying: "onplaying",
		onPopState: "onpopstate",
		onProgress: "onprogress",
		onRateChange: "onratechange",
		onRepeat: "onrepeat",
		onReset: "onreset",
		onResize: "onresize",
		onScroll: "onscroll",
		onSeeked: "onseeked",
		onSeeking: "onseeking",
		onSelect: "onselect",
		onShow: "onshow",
		onStalled: "onstalled",
		onStorage: "onstorage",
		onSubmit: "onsubmit",
		onSuspend: "onsuspend",
		onTimeUpdate: "ontimeupdate",
		onToggle: "ontoggle",
		onUnload: "onunload",
		onVolumeChange: "onvolumechange",
		onWaiting: "onwaiting",
		onZoom: "onzoom",
		overlinePosition: "overline-position",
		overlineThickness: "overline-thickness",
		paintOrder: "paint-order",
		panose1: "panose-1",
		pointerEvents: "pointer-events",
		referrerPolicy: "referrerpolicy",
		renderingIntent: "rendering-intent",
		shapeRendering: "shape-rendering",
		stopColor: "stop-color",
		stopOpacity: "stop-opacity",
		strikethroughPosition: "strikethrough-position",
		strikethroughThickness: "strikethrough-thickness",
		strokeDashArray: "stroke-dasharray",
		strokeDashOffset: "stroke-dashoffset",
		strokeLineCap: "stroke-linecap",
		strokeLineJoin: "stroke-linejoin",
		strokeMiterLimit: "stroke-miterlimit",
		strokeOpacity: "stroke-opacity",
		strokeWidth: "stroke-width",
		tabIndex: "tabindex",
		textAnchor: "text-anchor",
		textDecoration: "text-decoration",
		textRendering: "text-rendering",
		transformOrigin: "transform-origin",
		typeOf: "typeof",
		underlinePosition: "underline-position",
		underlineThickness: "underline-thickness",
		unicodeBidi: "unicode-bidi",
		unicodeRange: "unicode-range",
		unitsPerEm: "units-per-em",
		vAlphabetic: "v-alphabetic",
		vHanging: "v-hanging",
		vIdeographic: "v-ideographic",
		vMathematical: "v-mathematical",
		vectorEffect: "vector-effect",
		vertAdvY: "vert-adv-y",
		vertOriginX: "vert-origin-x",
		vertOriginY: "vert-origin-y",
		wordSpacing: "word-spacing",
		writingMode: "writing-mode",
		xHeight: "x-height",
		playbackOrder: "playbackorder",
		timelineBegin: "timelinebegin"
	},
	properties: {
		about: ma,
		accentHeight: V,
		accumulate: null,
		additive: null,
		alignmentBaseline: null,
		alphabetic: V,
		amplitude: V,
		arabicForm: null,
		ascent: V,
		attributeName: null,
		attributeType: null,
		azimuth: V,
		bandwidth: null,
		baselineShift: null,
		baseFrequency: null,
		baseProfile: null,
		bbox: null,
		begin: null,
		bias: V,
		by: null,
		calcMode: null,
		capHeight: V,
		className: fa,
		clip: null,
		clipPath: null,
		clipPathUnits: null,
		clipRule: null,
		color: null,
		colorInterpolation: null,
		colorInterpolationFilters: null,
		colorProfile: null,
		colorRendering: null,
		content: null,
		contentScriptType: null,
		contentStyleType: null,
		crossOrigin: null,
		cursor: null,
		cx: null,
		cy: null,
		d: null,
		dataType: null,
		defaultAction: null,
		descent: V,
		diffuseConstant: V,
		direction: null,
		display: null,
		dur: null,
		divisor: V,
		dominantBaseline: null,
		download: B,
		dx: null,
		dy: null,
		edgeMode: null,
		editable: null,
		elevation: V,
		enableBackground: null,
		end: null,
		event: null,
		exponent: V,
		externalResourcesRequired: null,
		fill: null,
		fillOpacity: V,
		fillRule: null,
		filter: null,
		filterRes: null,
		filterUnits: null,
		floodColor: null,
		floodOpacity: null,
		focusable: null,
		focusHighlight: null,
		fontFamily: null,
		fontSize: null,
		fontSizeAdjust: null,
		fontStretch: null,
		fontStyle: null,
		fontVariant: null,
		fontWeight: null,
		format: null,
		fr: null,
		from: null,
		fx: null,
		fy: null,
		g1: pa,
		g2: pa,
		glyphName: pa,
		glyphOrientationHorizontal: null,
		glyphOrientationVertical: null,
		glyphRef: null,
		gradientTransform: null,
		gradientUnits: null,
		handler: null,
		hanging: V,
		hatchContentUnits: null,
		hatchUnits: null,
		height: null,
		href: null,
		hrefLang: null,
		horizAdvX: V,
		horizOriginX: V,
		horizOriginY: V,
		id: null,
		ideographic: V,
		imageRendering: null,
		initialVisibility: null,
		in: null,
		in2: null,
		intercept: V,
		k: V,
		k1: V,
		k2: V,
		k3: V,
		k4: V,
		kernelMatrix: ma,
		kernelUnitLength: null,
		keyPoints: null,
		keySplines: null,
		keyTimes: null,
		kerning: null,
		lang: null,
		lengthAdjust: null,
		letterSpacing: null,
		lightingColor: null,
		limitingConeAngle: V,
		local: null,
		markerEnd: null,
		markerMid: null,
		markerStart: null,
		markerHeight: null,
		markerUnits: null,
		markerWidth: null,
		mask: null,
		maskContentUnits: null,
		maskType: null,
		maskUnits: null,
		mathematical: null,
		max: null,
		media: null,
		mediaCharacterEncoding: null,
		mediaContentEncodings: null,
		mediaSize: V,
		mediaTime: null,
		method: null,
		min: null,
		mode: null,
		name: null,
		navDown: null,
		navDownLeft: null,
		navDownRight: null,
		navLeft: null,
		navNext: null,
		navPrev: null,
		navRight: null,
		navUp: null,
		navUpLeft: null,
		navUpRight: null,
		numOctaves: null,
		observer: null,
		offset: null,
		onAbort: null,
		onActivate: null,
		onAfterPrint: null,
		onBeforePrint: null,
		onBegin: null,
		onCancel: null,
		onCanPlay: null,
		onCanPlayThrough: null,
		onChange: null,
		onClick: null,
		onClose: null,
		onCopy: null,
		onCueChange: null,
		onCut: null,
		onDblClick: null,
		onDrag: null,
		onDragEnd: null,
		onDragEnter: null,
		onDragExit: null,
		onDragLeave: null,
		onDragOver: null,
		onDragStart: null,
		onDrop: null,
		onDurationChange: null,
		onEmptied: null,
		onEnd: null,
		onEnded: null,
		onError: null,
		onFocus: null,
		onFocusIn: null,
		onFocusOut: null,
		onHashChange: null,
		onInput: null,
		onInvalid: null,
		onKeyDown: null,
		onKeyPress: null,
		onKeyUp: null,
		onLoad: null,
		onLoadedData: null,
		onLoadedMetadata: null,
		onLoadStart: null,
		onMessage: null,
		onMouseDown: null,
		onMouseEnter: null,
		onMouseLeave: null,
		onMouseMove: null,
		onMouseOut: null,
		onMouseOver: null,
		onMouseUp: null,
		onMouseWheel: null,
		onOffline: null,
		onOnline: null,
		onPageHide: null,
		onPageShow: null,
		onPaste: null,
		onPause: null,
		onPlay: null,
		onPlaying: null,
		onPopState: null,
		onProgress: null,
		onRateChange: null,
		onRepeat: null,
		onReset: null,
		onResize: null,
		onScroll: null,
		onSeeked: null,
		onSeeking: null,
		onSelect: null,
		onShow: null,
		onStalled: null,
		onStorage: null,
		onSubmit: null,
		onSuspend: null,
		onTimeUpdate: null,
		onToggle: null,
		onUnload: null,
		onVolumeChange: null,
		onWaiting: null,
		onZoom: null,
		opacity: null,
		operator: null,
		order: null,
		orient: null,
		orientation: null,
		origin: null,
		overflow: null,
		overlay: null,
		overlinePosition: V,
		overlineThickness: V,
		paintOrder: null,
		panose1: null,
		path: null,
		pathLength: V,
		patternContentUnits: null,
		patternTransform: null,
		patternUnits: null,
		phase: null,
		ping: fa,
		pitch: null,
		playbackOrder: null,
		pointerEvents: null,
		points: null,
		pointsAtX: V,
		pointsAtY: V,
		pointsAtZ: V,
		preserveAlpha: null,
		preserveAspectRatio: null,
		primitiveUnits: null,
		propagate: null,
		property: ma,
		r: null,
		radius: null,
		referrerPolicy: null,
		refX: null,
		refY: null,
		rel: ma,
		rev: ma,
		renderingIntent: null,
		repeatCount: null,
		repeatDur: null,
		requiredExtensions: ma,
		requiredFeatures: ma,
		requiredFonts: ma,
		requiredFormats: ma,
		resource: null,
		restart: null,
		result: null,
		rotate: null,
		rx: null,
		ry: null,
		scale: null,
		seed: null,
		shapeRendering: null,
		side: null,
		slope: null,
		snapshotTime: null,
		specularConstant: V,
		specularExponent: V,
		spreadMethod: null,
		spacing: null,
		startOffset: null,
		stdDeviation: null,
		stemh: null,
		stemv: null,
		stitchTiles: null,
		stopColor: null,
		stopOpacity: null,
		strikethroughPosition: V,
		strikethroughThickness: V,
		string: null,
		stroke: null,
		strokeDashArray: ma,
		strokeDashOffset: null,
		strokeLineCap: null,
		strokeLineJoin: null,
		strokeMiterLimit: V,
		strokeOpacity: V,
		strokeWidth: null,
		style: null,
		surfaceScale: V,
		syncBehavior: null,
		syncBehaviorDefault: null,
		syncMaster: null,
		syncTolerance: null,
		syncToleranceDefault: null,
		systemLanguage: ma,
		tabIndex: V,
		tableValues: null,
		target: null,
		targetX: V,
		targetY: V,
		textAnchor: null,
		textDecoration: null,
		textRendering: null,
		textLength: null,
		timelineBegin: null,
		title: null,
		transformBehavior: null,
		type: null,
		typeOf: ma,
		to: null,
		transform: null,
		transformOrigin: null,
		u1: null,
		u2: null,
		underlinePosition: V,
		underlineThickness: V,
		unicode: null,
		unicodeBidi: null,
		unicodeRange: null,
		unitsPerEm: V,
		values: null,
		vAlphabetic: V,
		vMathematical: V,
		vectorEffect: null,
		vHanging: V,
		vIdeographic: V,
		version: null,
		vertAdvY: V,
		vertOriginX: V,
		vertOriginY: V,
		viewBox: null,
		viewTarget: null,
		visibility: null,
		width: null,
		widths: null,
		wordSpacing: null,
		writingMode: null,
		x: null,
		x1: null,
		x2: null,
		xChannelSelector: null,
		xHeight: V,
		y: null,
		y1: null,
		y2: null,
		yChannelSelector: null,
		z: null,
		zoomAndPan: null
	},
	space: "svg",
	transform: xa
}), Ta = ya({
	properties: {
		xLinkActuate: null,
		xLinkArcRole: null,
		xLinkHref: null,
		xLinkRole: null,
		xLinkShow: null,
		xLinkTitle: null,
		xLinkType: null
	},
	space: "xlink",
	transform(e, t) {
		return "xlink:" + t.slice(5).toLowerCase();
	}
}), Ea = ya({
	attributes: { xmlnsxlink: "xmlns:xlink" },
	properties: {
		xmlnsXLink: null,
		xmlns: null
	},
	space: "xmlns",
	transform: Sa
}), Da = ya({
	properties: {
		xmlBase: null,
		xmlLang: null,
		xmlSpace: null
	},
	space: "xml",
	transform(e, t) {
		return "xml:" + t.slice(3).toLowerCase();
	}
}), Oa = {
	classId: "classID",
	dataType: "datatype",
	itemId: "itemID",
	strokeDashArray: "strokeDasharray",
	strokeDashOffset: "strokeDashoffset",
	strokeLineCap: "strokeLinecap",
	strokeLineJoin: "strokeLinejoin",
	strokeMiterLimit: "strokeMiterlimit",
	typeOf: "typeof",
	xLinkActuate: "xlinkActuate",
	xLinkArcRole: "xlinkArcrole",
	xLinkHref: "xlinkHref",
	xLinkRole: "xlinkRole",
	xLinkShow: "xlinkShow",
	xLinkTitle: "xlinkTitle",
	xLinkType: "xlinkType",
	xmlnsXLink: "xmlnsXlink"
}, ka = /[A-Z]/g, Aa = /-[a-z]/g, ja = /^data[-\w.:]+$/i;
function Ma(e, t) {
	let n = oa(t), r = t, i = sa;
	if (n in e.normal) return e.property[e.normal[n]];
	if (n.length > 4 && n.slice(0, 4) === "data" && ja.test(t)) {
		if (t.charAt(4) === "-") {
			let e = t.slice(5).replace(Aa, Pa);
			r = "data" + e.charAt(0).toUpperCase() + e.slice(1);
		} else {
			let e = t.slice(4);
			if (!Aa.test(e)) {
				let n = e.replace(ka, Na);
				n.charAt(0) !== "-" && (n = "-" + n), t = "data" + n;
			}
		}
		i = _a;
	}
	return new i(r, t);
}
function Na(e) {
	return "-" + e.toLowerCase();
}
function Pa(e) {
	return e.charAt(1).toUpperCase();
}
//#endregion
//#region node_modules/property-information/index.js
var Fa = aa([
	ba,
	Ca,
	Ta,
	Ea,
	Da
], "html"), Ia = aa([
	ba,
	wa,
	Ta,
	Ea,
	Da
], "svg");
//#endregion
//#region node_modules/space-separated-tokens/index.js
function La(e) {
	return e.join(" ").trim();
}
//#endregion
//#region node_modules/inline-style-parser/cjs/index.js
var Ra = /* @__PURE__ */ n(((e, t) => {
	var n = /\/\*[^*]*\*+([^/*][^*]*\*+)*\//g, r = /\n/g, i = /^\s*/, a = /^(\*?[-#/*\\\w]+(\[[0-9a-z_-]+\])?)\s*/, o = /^:\s*/, s = /^((?:'(?:\\'|.)*?'|"(?:\\"|.)*?"|\([^)]*?\)|[^};])+)/, c = /^[;\s]*/, l = /^\s+|\s+$/g;
	function u(e, t) {
		if (typeof e != "string") throw TypeError("First argument must be a string");
		if (!e) return [];
		t ||= {};
		var l = 1, u = 1;
		function f(e) {
			var t = e.match(r);
			t && (l += t.length);
			var n = e.lastIndexOf("\n");
			u = ~n ? e.length - n : u + e.length;
		}
		function p() {
			var e = {
				line: l,
				column: u
			};
			return function(t) {
				return t.position = new m(e), _(), t;
			};
		}
		function m(e) {
			this.start = e, this.end = {
				line: l,
				column: u
			}, this.source = t.source;
		}
		m.prototype.content = e;
		function h(n) {
			var r = /* @__PURE__ */ Error(t.source + ":" + l + ":" + u + ": " + n);
			if (r.reason = n, r.filename = t.source, r.line = l, r.column = u, r.source = e, !t.silent) throw r;
		}
		function g(t) {
			var n = t.exec(e);
			if (n) {
				var r = n[0];
				return f(r), e = e.slice(r.length), n;
			}
		}
		function _() {
			g(i);
		}
		function v(e) {
			var t;
			for (e ||= []; t = y();) t !== !1 && e.push(t);
			return e;
		}
		function y() {
			var t = p();
			if (!(e.charAt(0) != "/" || e.charAt(1) != "*")) {
				for (var n = 2; e.charAt(n) != "" && (e.charAt(n) != "*" || e.charAt(n + 1) != "/");) ++n;
				if (n += 2, e.charAt(n - 1) === "") return h("End of comment missing");
				var r = e.slice(2, n - 2);
				return u += 2, f(r), e = e.slice(n), u += 2, t({
					type: "comment",
					comment: r
				});
			}
		}
		function b() {
			var e = p(), t = g(a);
			if (t) {
				if (y(), !g(o)) return h("property missing ':'");
				var r = g(s), i = e({
					type: "declaration",
					property: d(t[0].replace(n, "")),
					value: r ? d(r[0].replace(n, "")) : ""
				});
				return g(c), i;
			}
		}
		function x() {
			var e = [];
			v(e);
			for (var t; t = b();) t !== !1 && (e.push(t), v(e));
			return e;
		}
		return _(), x();
	}
	function d(e) {
		return e ? e.replace(l, "") : "";
	}
	t.exports = u;
})), za = /* @__PURE__ */ n(((e) => {
	var t = e && e.__importDefault || function(e) {
		return e && e.__esModule ? e : { default: e };
	};
	Object.defineProperty(e, "__esModule", { value: !0 }), e.default = r;
	var n = t(Ra());
	function r(e, t) {
		let r = null;
		if (!e || typeof e != "string") return r;
		let i = (0, n.default)(e), a = typeof t == "function";
		return i.forEach((e) => {
			if (e.type !== "declaration") return;
			let { property: n, value: i } = e;
			a ? t(n, i, e) : i && (r ||= {}, r[n] = i);
		}), r;
	}
})), Ba = /* @__PURE__ */ n(((e) => {
	Object.defineProperty(e, "__esModule", { value: !0 }), e.camelCase = void 0;
	var t = /^--[a-zA-Z0-9_-]+$/, n = /-([a-z])/g, r = /^[^-]+$/, i = /^-(webkit|moz|ms|o|khtml)-/, a = /^-(ms)-/, o = function(e) {
		return !e || r.test(e) || t.test(e);
	}, s = function(e, t) {
		return t.toUpperCase();
	}, c = function(e, t) {
		return `${t}-`;
	};
	e.camelCase = function(e, t) {
		return t === void 0 && (t = {}), o(e) ? e : (e = e.toLowerCase(), e = t.reactCompat ? e.replace(a, c) : e.replace(i, c), e.replace(n, s));
	};
})), Va = /* @__PURE__ */ n(((e, t) => {
	var n = (e && e.__importDefault || function(e) {
		return e && e.__esModule ? e : { default: e };
	})(za()), r = Ba();
	function i(e, t) {
		var i = {};
		return !e || typeof e != "string" || (0, n.default)(e, function(e, n) {
			e && n && (i[(0, r.camelCase)(e, t)] = n);
		}), i;
	}
	i.default = i, t.exports = i;
})), Ha = Wa("end"), Ua = Wa("start");
function Wa(e) {
	return t;
	function t(t) {
		let n = t && t.position && t.position[e] || {};
		if (typeof n.line == "number" && n.line > 0 && typeof n.column == "number" && n.column > 0) return {
			line: n.line,
			column: n.column,
			offset: typeof n.offset == "number" && n.offset > -1 ? n.offset : void 0
		};
	}
}
function Ga(e) {
	let t = Ua(e), n = Ha(e);
	if (t && n) return {
		start: t,
		end: n
	};
}
//#endregion
//#region node_modules/unist-util-stringify-position/lib/index.js
function Ka(e) {
	return !e || typeof e != "object" ? "" : "position" in e || "type" in e ? Ja(e.position) : "start" in e || "end" in e ? Ja(e) : "line" in e || "column" in e ? qa(e) : "";
}
function qa(e) {
	return Ya(e && e.line) + ":" + Ya(e && e.column);
}
function Ja(e) {
	return qa(e && e.start) + "-" + qa(e && e.end);
}
function Ya(e) {
	return e && typeof e == "number" ? e : 1;
}
//#endregion
//#region node_modules/vfile-message/lib/index.js
var Xa = class extends Error {
	constructor(e, t, n) {
		super(), typeof t == "string" && (n = t, t = void 0);
		let r = "", i = {}, a = !1;
		if (t && (i = "line" in t && "column" in t || "start" in t && "end" in t ? { place: t } : "type" in t ? {
			ancestors: [t],
			place: t.position
		} : { ...t }), typeof e == "string" ? r = e : !i.cause && e && (a = !0, r = e.message, i.cause = e), !i.ruleId && !i.source && typeof n == "string") {
			let e = n.indexOf(":");
			e === -1 ? i.ruleId = n : (i.source = n.slice(0, e), i.ruleId = n.slice(e + 1));
		}
		if (!i.place && i.ancestors && i.ancestors) {
			let e = i.ancestors[i.ancestors.length - 1];
			e && (i.place = e.position);
		}
		let o = i.place && "start" in i.place ? i.place.start : i.place;
		this.ancestors = i.ancestors || void 0, this.cause = i.cause || void 0, this.column = o ? o.column : void 0, this.fatal = void 0, this.file = "", this.message = r, this.line = o ? o.line : void 0, this.name = Ka(i.place) || "1:1", this.place = i.place || void 0, this.reason = this.message, this.ruleId = i.ruleId || void 0, this.source = i.source || void 0, this.stack = a && i.cause && typeof i.cause.stack == "string" ? i.cause.stack : "", this.actual = void 0, this.expected = void 0, this.note = void 0, this.url = void 0;
	}
};
Xa.prototype.file = "", Xa.prototype.name = "", Xa.prototype.reason = "", Xa.prototype.message = "", Xa.prototype.stack = "", Xa.prototype.column = void 0, Xa.prototype.line = void 0, Xa.prototype.ancestors = void 0, Xa.prototype.cause = void 0, Xa.prototype.fatal = void 0, Xa.prototype.place = void 0, Xa.prototype.ruleId = void 0, Xa.prototype.source = void 0;
//#endregion
//#region node_modules/hast-util-to-jsx-runtime/lib/index.js
var Za = /* @__PURE__ */ e(Va(), 1), Qa = {}.hasOwnProperty, $a = /* @__PURE__ */ new Map(), eo = /[A-Z]/g, to = /* @__PURE__ */ new Set([
	"table",
	"tbody",
	"thead",
	"tfoot",
	"tr"
]), no = /* @__PURE__ */ new Set(["td", "th"]);
function ro(e, t) {
	if (!t || t.Fragment === void 0) throw TypeError("Expected `Fragment` in options");
	let n = t.filePath || void 0, r;
	if (t.development) {
		if (typeof t.jsxDEV != "function") throw TypeError("Expected `jsxDEV` in options when `development: true`");
		r = mo(n, t.jsxDEV);
	} else {
		if (typeof t.jsx != "function") throw TypeError("Expected `jsx` in production options");
		if (typeof t.jsxs != "function") throw TypeError("Expected `jsxs` in production options");
		r = po(n, t.jsx, t.jsxs);
	}
	let i = {
		Fragment: t.Fragment,
		ancestors: [],
		components: t.components || {},
		create: r,
		elementAttributeNameCase: t.elementAttributeNameCase || "react",
		evaluater: t.createEvaluater ? t.createEvaluater() : void 0,
		filePath: n,
		ignoreInvalidStyle: t.ignoreInvalidStyle || !1,
		passKeys: t.passKeys !== !1,
		passNode: t.passNode || !1,
		schema: t.space === "svg" ? Ia : Fa,
		stylePropertyNameCase: t.stylePropertyNameCase || "dom",
		tableCellAlignToStyle: t.tableCellAlignToStyle !== !1
	}, a = io(i, e, void 0);
	return a && typeof a != "string" ? a : i.create(e, i.Fragment, { children: a || void 0 }, void 0);
}
function io(e, t, n) {
	if (t.type === "element") return ao(e, t, n);
	if (t.type === "mdxFlowExpression" || t.type === "mdxTextExpression") return oo(e, t);
	if (t.type === "mdxJsxFlowElement" || t.type === "mdxJsxTextElement") return co(e, t, n);
	if (t.type === "mdxjsEsm") return so(e, t);
	if (t.type === "root") return lo(e, t, n);
	if (t.type === "text") return uo(e, t);
}
function ao(e, t, n) {
	let r = e.schema, i = r;
	t.tagName.toLowerCase() === "svg" && r.space === "html" && (i = Ia, e.schema = i), e.ancestors.push(t);
	let a = bo(e, t.tagName, !1), o = ho(e, t), s = _o(e, t);
	return to.has(t.tagName) && (s = s.filter(function(e) {
		return typeof e != "string" || !na(e);
	})), H(e, o, a, t), fo(o, s), e.ancestors.pop(), e.schema = r, e.create(t, a, o, n);
}
function oo(e, t) {
	if (t.data && t.data.estree && e.evaluater) {
		let n = t.data.estree.body[0];
		return n.type, e.evaluater.evaluateExpression(n.expression);
	}
	xo(e, t.position);
}
function so(e, t) {
	if (t.data && t.data.estree && e.evaluater) return e.evaluater.evaluateProgram(t.data.estree);
	xo(e, t.position);
}
function co(e, t, n) {
	let r = e.schema, i = r;
	t.name === "svg" && r.space === "html" && (i = Ia, e.schema = i), e.ancestors.push(t);
	let a = t.name === null ? e.Fragment : bo(e, t.name, !0), o = go(e, t), s = _o(e, t);
	return H(e, o, a, t), fo(o, s), e.ancestors.pop(), e.schema = r, e.create(t, a, o, n);
}
function lo(e, t, n) {
	let r = {};
	return fo(r, _o(e, t)), e.create(t, e.Fragment, r, n);
}
function uo(e, t) {
	return t.value;
}
function H(e, t, n, r) {
	typeof n != "string" && n !== e.Fragment && e.passNode && (t.node = r);
}
function fo(e, t) {
	if (t.length > 0) {
		let n = t.length > 1 ? t : t[0];
		n && (e.children = n);
	}
}
function po(e, t, n) {
	return r;
	function r(e, r, i, a) {
		let o = Array.isArray(i.children) ? n : t;
		return a ? o(r, i, a) : o(r, i);
	}
}
function mo(e, t) {
	return n;
	function n(n, r, i, a) {
		let o = Array.isArray(i.children), s = Ua(n);
		return t(r, i, a, o, {
			columnNumber: s ? s.column - 1 : void 0,
			fileName: e,
			lineNumber: s ? s.line : void 0
		}, void 0);
	}
}
function ho(e, t) {
	let n = {}, r, i;
	for (i in t.properties) if (i !== "children" && Qa.call(t.properties, i)) {
		let a = vo(e, i, t.properties[i]);
		if (a) {
			let [i, o] = a;
			e.tableCellAlignToStyle && i === "align" && typeof o == "string" && no.has(t.tagName) ? r = o : n[i] = o;
		}
	}
	if (r) {
		let t = n.style ||= {};
		t[e.stylePropertyNameCase === "css" ? "text-align" : "textAlign"] = r;
	}
	return n;
}
function go(e, t) {
	let n = {};
	for (let r of t.attributes) if (r.type === "mdxJsxExpressionAttribute") if (r.data && r.data.estree && e.evaluater) {
		let t = r.data.estree.body[0];
		t.type;
		let i = t.expression;
		i.type;
		let a = i.properties[0];
		a.type, Object.assign(n, e.evaluater.evaluateExpression(a.argument));
	} else xo(e, t.position);
	else {
		let i = r.name, a;
		if (r.value && typeof r.value == "object") if (r.value.data && r.value.data.estree && e.evaluater) {
			let t = r.value.data.estree.body[0];
			t.type, a = e.evaluater.evaluateExpression(t.expression);
		} else xo(e, t.position);
		else a = r.value === null || r.value;
		n[i] = a;
	}
	return n;
}
function _o(e, t) {
	let n = [], r = -1, i = e.passKeys ? /* @__PURE__ */ new Map() : $a;
	for (; ++r < t.children.length;) {
		let a = t.children[r], o;
		if (e.passKeys) {
			let e = a.type === "element" ? a.tagName : a.type === "mdxJsxFlowElement" || a.type === "mdxJsxTextElement" ? a.name : void 0;
			if (e) {
				let t = i.get(e) || 0;
				o = e + "-" + t, i.set(e, t + 1);
			}
		}
		let s = io(e, a, o);
		s !== void 0 && n.push(s);
	}
	return n;
}
function vo(e, t, n) {
	let r = Ma(e.schema, t);
	if (!(n == null || typeof n == "number" && Number.isNaN(n))) {
		if (Array.isArray(n) && (n = r.commaSeparated ? Xi(n) : La(n)), r.property === "style") {
			let t = typeof n == "object" ? n : yo(e, String(n));
			return e.stylePropertyNameCase === "css" && (t = So(t)), ["style", t];
		}
		return [e.elementAttributeNameCase === "react" && r.space ? Oa[r.property] || r.property : r.attribute, n];
	}
}
function yo(e, t) {
	try {
		return (0, Za.default)(t, { reactCompat: !0 });
	} catch (t) {
		if (e.ignoreInvalidStyle) return {};
		let n = t, r = new Xa("Cannot parse `style` attribute", {
			ancestors: e.ancestors,
			cause: n,
			ruleId: "style",
			source: "hast-util-to-jsx-runtime"
		});
		throw r.file = e.filePath || void 0, r.url = "https://github.com/syntax-tree/hast-util-to-jsx-runtime#cannot-parse-style-attribute", r;
	}
}
function bo(e, t, n) {
	let r;
	if (!n) r = {
		type: "Literal",
		value: t
	};
	else if (t.includes(".")) {
		let e = t.split("."), n = -1, i;
		for (; ++n < e.length;) {
			let t = ea(e[n]) ? {
				type: "Identifier",
				name: e[n]
			} : {
				type: "Literal",
				value: e[n]
			};
			i = i ? {
				type: "MemberExpression",
				object: i,
				property: t,
				computed: !!(n && t.type === "Literal"),
				optional: !1
			} : t;
		}
		r = i;
	} else r = ea(t) && !/^[a-z]/.test(t) ? {
		type: "Identifier",
		name: t
	} : {
		type: "Literal",
		value: t
	};
	if (r.type === "Literal") {
		let t = r.value;
		return Qa.call(e.components, t) ? e.components[t] : t;
	}
	if (e.evaluater) return e.evaluater.evaluateExpression(r);
	xo(e);
}
function xo(e, t) {
	let n = new Xa("Cannot handle MDX estrees without `createEvaluater`", {
		ancestors: e.ancestors,
		place: t,
		ruleId: "mdx-estree",
		source: "hast-util-to-jsx-runtime"
	});
	throw n.file = e.filePath || void 0, n.url = "https://github.com/syntax-tree/hast-util-to-jsx-runtime#cannot-handle-mdx-estrees-without-createevaluater", n;
}
function So(e) {
	let t = {}, n;
	for (n in e) Qa.call(e, n) && (t[Co(n)] = e[n]);
	return t;
}
function Co(e) {
	let t = e.replace(eo, wo);
	return t.slice(0, 3) === "ms-" && (t = "-" + t), t;
}
function wo(e) {
	return "-" + e.toLowerCase();
}
//#endregion
//#region node_modules/html-url-attributes/lib/index.js
var To = {
	action: ["form"],
	cite: [
		"blockquote",
		"del",
		"ins",
		"q"
	],
	data: ["object"],
	formAction: ["button", "input"],
	href: [
		"a",
		"area",
		"base",
		"link"
	],
	icon: ["menuitem"],
	itemId: null,
	manifest: ["html"],
	ping: ["a", "area"],
	poster: ["video"],
	src: [
		"audio",
		"embed",
		"iframe",
		"img",
		"input",
		"script",
		"source",
		"track",
		"video"
	]
}, Eo = /* @__PURE__ */ n(((e) => {
	var t = Symbol.for("react.transitional.element"), n = Symbol.for("react.fragment");
	function r(e, n, r) {
		var i = null;
		if (r !== void 0 && (i = "" + r), n.key !== void 0 && (i = "" + n.key), "key" in n) for (var a in r = {}, n) a !== "key" && (r[a] = n[a]);
		else r = n;
		return n = r.ref, {
			$$typeof: t,
			type: e,
			key: i,
			ref: n === void 0 ? null : n,
			props: r
		};
	}
	e.Fragment = n, e.jsx = r, e.jsxs = r;
})), Do = /* @__PURE__ */ n(((e, t) => {
	t.exports = Eo();
})), Oo = {};
function ko(e, t) {
	let n = t || Oo;
	return Ao(e, typeof n.includeImageAlt != "boolean" || n.includeImageAlt, typeof n.includeHtml != "boolean" || n.includeHtml);
}
function Ao(e, t, n) {
	if (Mo(e)) {
		if ("value" in e) return e.type === "html" && !n ? "" : e.value;
		if (t && "alt" in e && e.alt) return e.alt;
		if ("children" in e) return jo(e.children, t, n);
	}
	return Array.isArray(e) ? jo(e, t, n) : "";
}
function jo(e, t, n) {
	let r = [], i = -1;
	for (; ++i < e.length;) r[i] = Ao(e[i], t, n);
	return r.join("");
}
function Mo(e) {
	return !!(e && typeof e == "object");
}
//#endregion
//#region node_modules/decode-named-character-reference/index.dom.js
var No = document.createElement("i");
function Po(e) {
	let t = "&" + e + ";";
	No.innerHTML = t;
	let n = No.textContent;
	return n.charCodeAt(n.length - 1) === 59 && e !== "semi" ? !1 : n !== t && n;
}
//#endregion
//#region node_modules/micromark-util-chunked/index.js
function Fo(e, t, n, r) {
	let i = e.length, a = 0, o;
	if (t = t < 0 ? -t > i ? 0 : i + t : t > i ? i : t, n = n > 0 ? n : 0, r.length < 1e4) o = Array.from(r), o.unshift(t, n), e.splice(...o);
	else for (n && e.splice(t, n); a < r.length;) o = r.slice(a, a + 1e4), o.unshift(t, 0), e.splice(...o), a += 1e4, t += 1e4;
}
function Io(e, t) {
	return e.length > 0 ? (Fo(e, e.length, 0, t), e) : t;
}
//#endregion
//#region node_modules/micromark-util-combine-extensions/index.js
var Lo = {}.hasOwnProperty;
function Ro(e) {
	let t = {}, n = -1;
	for (; ++n < e.length;) zo(t, e[n]);
	return t;
}
function zo(e, t) {
	let n;
	for (n in t) {
		let r = (Lo.call(e, n) ? e[n] : void 0) || (e[n] = {}), i = t[n], a;
		if (i) for (a in i) {
			Lo.call(r, a) || (r[a] = []);
			let e = i[a];
			Bo(r[a], Array.isArray(e) ? e : e ? [e] : []);
		}
	}
}
function Bo(e, t) {
	let n = -1, r = [];
	for (; ++n < t.length;) (t[n].add === "after" ? e : r).push(t[n]);
	Fo(e, 0, 0, r);
}
//#endregion
//#region node_modules/micromark-util-decode-numeric-character-reference/index.js
function Vo(e, t) {
	let n = Number.parseInt(e, t);
	return n < 9 || n === 11 || n > 13 && n < 32 || n > 126 && n < 160 || n > 55295 && n < 57344 || n > 64975 && n < 65008 || (n & 65535) == 65535 || (n & 65535) == 65534 || n > 1114111 ? "�" : String.fromCodePoint(n);
}
//#endregion
//#region node_modules/micromark-util-normalize-identifier/index.js
function Ho(e) {
	return e.replace(/[\t\n\r ]+/g, " ").replace(/^ | $/g, "").toLowerCase().toUpperCase();
}
//#endregion
//#region node_modules/micromark-util-character/index.js
var Uo = $o(/[A-Za-z]/), Wo = $o(/[\dA-Za-z]/), Go = $o(/[#-'*+\--9=?A-Z^-~]/);
function Ko(e) {
	return e !== null && (e < 32 || e === 127);
}
var qo = $o(/\d/), Jo = $o(/[\dA-Fa-f]/), Yo = $o(/[!-/:-@[-`{-~]/);
function U(e) {
	return e !== null && e < -2;
}
function Xo(e) {
	return e !== null && (e < 0 || e === 32);
}
function W(e) {
	return e === -2 || e === -1 || e === 32;
}
var Zo = $o(/\p{P}|\p{S}/u), Qo = $o(/\s/);
function $o(e) {
	return t;
	function t(t) {
		return t !== null && t > -1 && e.test(String.fromCharCode(t));
	}
}
//#endregion
//#region node_modules/micromark-util-sanitize-uri/index.js
function es(e) {
	let t = [], n = -1, r = 0, i = 0;
	for (; ++n < e.length;) {
		let a = e.charCodeAt(n), o = "";
		if (a === 37 && Wo(e.charCodeAt(n + 1)) && Wo(e.charCodeAt(n + 2))) i = 2;
		else if (a < 128) /[!#$&-;=?-Z_a-z~]/.test(String.fromCharCode(a)) || (o = String.fromCharCode(a));
		else if (a > 55295 && a < 57344) {
			let t = e.charCodeAt(n + 1);
			a < 56320 && t > 56319 && t < 57344 ? (o = String.fromCharCode(a, t), i = 1) : o = "�";
		} else o = String.fromCharCode(a);
		o &&= (t.push(e.slice(r, n), encodeURIComponent(o)), r = n + i + 1, ""), i &&= (n += i, 0);
	}
	return t.join("") + e.slice(r);
}
//#endregion
//#region node_modules/micromark-factory-space/index.js
function G(e, t, n, r) {
	let i = r ? r - 1 : Infinity, a = 0;
	return o;
	function o(r) {
		return W(r) ? (e.enter(n), s(r)) : t(r);
	}
	function s(r) {
		return W(r) && a++ < i ? (e.consume(r), s) : (e.exit(n), t(r));
	}
}
//#endregion
//#region node_modules/micromark/lib/initialize/content.js
var ts = { tokenize: ns };
function ns(e) {
	let t = e.attempt(this.parser.constructs.contentInitial, r, i), n;
	return t;
	function r(n) {
		if (n === null) {
			e.consume(n);
			return;
		}
		return e.enter("lineEnding"), e.consume(n), e.exit("lineEnding"), G(e, t, "linePrefix");
	}
	function i(t) {
		return e.enter("paragraph"), a(t);
	}
	function a(t) {
		let r = e.enter("chunkText", {
			contentType: "text",
			previous: n
		});
		return n && (n.next = r), n = r, o(t);
	}
	function o(t) {
		if (t === null) {
			e.exit("chunkText"), e.exit("paragraph"), e.consume(t);
			return;
		}
		return U(t) ? (e.consume(t), e.exit("chunkText"), a) : (e.consume(t), o);
	}
}
//#endregion
//#region node_modules/micromark/lib/initialize/document.js
var rs = { tokenize: as }, is = { tokenize: os };
function as(e) {
	let t = this, n = [], r = 0, i, a, o;
	return s;
	function s(i) {
		if (r < n.length) {
			let a = n[r];
			return t.containerState = a[1], e.attempt(a[0].continuation, c, l)(i);
		}
		return l(i);
	}
	function c(e) {
		if (r++, t.containerState._closeFlow) {
			t.containerState._closeFlow = void 0, i && v();
			let n = t.events.length, a = n, o;
			for (; a--;) if (t.events[a][0] === "exit" && t.events[a][1].type === "chunkFlow") {
				o = t.events[a][1].end;
				break;
			}
			_(r);
			let s = n;
			for (; s < t.events.length;) t.events[s][1].end = { ...o }, s++;
			return Fo(t.events, a + 1, 0, t.events.slice(n)), t.events.length = s, l(e);
		}
		return s(e);
	}
	function l(a) {
		if (r === n.length) {
			if (!i) return f(a);
			if (i.currentConstruct && i.currentConstruct.concrete) return m(a);
			t.interrupt = !!(i.currentConstruct && !i._gfmTableDynamicInterruptHack);
		}
		return t.containerState = {}, e.check(is, u, d)(a);
	}
	function u(e) {
		return i && v(), _(r), f(e);
	}
	function d(e) {
		return t.parser.lazy[t.now().line] = r !== n.length, o = t.now().offset, m(e);
	}
	function f(n) {
		return t.containerState = {}, e.attempt(is, p, m)(n);
	}
	function p(e) {
		return r++, n.push([t.currentConstruct, t.containerState]), f(e);
	}
	function m(n) {
		if (n === null) {
			i && v(), _(0), e.consume(n);
			return;
		}
		return i ||= t.parser.flow(t.now()), e.enter("chunkFlow", {
			_tokenizer: i,
			contentType: "flow",
			previous: a
		}), h(n);
	}
	function h(n) {
		if (n === null) {
			g(e.exit("chunkFlow"), !0), _(0), e.consume(n);
			return;
		}
		return U(n) ? (e.consume(n), g(e.exit("chunkFlow")), r = 0, t.interrupt = void 0, s) : (e.consume(n), h);
	}
	function g(e, n) {
		let s = t.sliceStream(e);
		if (n && s.push(null), e.previous = a, a && (a.next = e), a = e, i.defineSkip(e.start), i.write(s), t.parser.lazy[e.start.line]) {
			let e = i.events.length;
			for (; e--;) if (i.events[e][1].start.offset < o && (!i.events[e][1].end || i.events[e][1].end.offset > o)) return;
			let n = t.events.length, a = n, s, c;
			for (; a--;) if (t.events[a][0] === "exit" && t.events[a][1].type === "chunkFlow") {
				if (s) {
					c = t.events[a][1].end;
					break;
				}
				s = !0;
			}
			for (_(r), e = n; e < t.events.length;) t.events[e][1].end = { ...c }, e++;
			Fo(t.events, a + 1, 0, t.events.slice(n)), t.events.length = e;
		}
	}
	function _(r) {
		let i = n.length;
		for (; i-- > r;) {
			let r = n[i];
			t.containerState = r[1], r[0].exit.call(t, e);
		}
		n.length = r;
	}
	function v() {
		i.write([null]), a = void 0, i = void 0, t.containerState._closeFlow = void 0;
	}
}
function os(e, t, n) {
	return G(e, e.attempt(this.parser.constructs.document, t, n), "linePrefix", this.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4);
}
//#endregion
//#region node_modules/micromark-util-classify-character/index.js
function ss(e) {
	if (e === null || Xo(e) || Qo(e)) return 1;
	if (Zo(e)) return 2;
}
//#endregion
//#region node_modules/micromark-util-resolve-all/index.js
function cs(e, t, n) {
	let r = [], i = -1;
	for (; ++i < e.length;) {
		let a = e[i].resolveAll;
		a && !r.includes(a) && (t = a(t, n), r.push(a));
	}
	return t;
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/attention.js
var ls = {
	name: "attention",
	resolveAll: us,
	tokenize: ds
};
function us(e, t) {
	let n = -1, r, i, a, o, s, c, l, u;
	for (; ++n < e.length;) if (e[n][0] === "enter" && e[n][1].type === "attentionSequence" && e[n][1]._close) {
		for (r = n; r--;) if (e[r][0] === "exit" && e[r][1].type === "attentionSequence" && e[r][1]._open && t.sliceSerialize(e[r][1]).charCodeAt(0) === t.sliceSerialize(e[n][1]).charCodeAt(0)) {
			if ((e[r][1]._close || e[n][1]._open) && (e[n][1].end.offset - e[n][1].start.offset) % 3 && !((e[r][1].end.offset - e[r][1].start.offset + e[n][1].end.offset - e[n][1].start.offset) % 3)) continue;
			c = e[r][1].end.offset - e[r][1].start.offset > 1 && e[n][1].end.offset - e[n][1].start.offset > 1 ? 2 : 1;
			let d = { ...e[r][1].end }, f = { ...e[n][1].start };
			fs(d, -c), fs(f, c), o = {
				type: c > 1 ? "strongSequence" : "emphasisSequence",
				start: d,
				end: { ...e[r][1].end }
			}, s = {
				type: c > 1 ? "strongSequence" : "emphasisSequence",
				start: { ...e[n][1].start },
				end: f
			}, a = {
				type: c > 1 ? "strongText" : "emphasisText",
				start: { ...e[r][1].end },
				end: { ...e[n][1].start }
			}, i = {
				type: c > 1 ? "strong" : "emphasis",
				start: { ...o.start },
				end: { ...s.end }
			}, e[r][1].end = { ...o.start }, e[n][1].start = { ...s.end }, l = [], e[r][1].end.offset - e[r][1].start.offset && (l = Io(l, [[
				"enter",
				e[r][1],
				t
			], [
				"exit",
				e[r][1],
				t
			]])), l = Io(l, [
				[
					"enter",
					i,
					t
				],
				[
					"enter",
					o,
					t
				],
				[
					"exit",
					o,
					t
				],
				[
					"enter",
					a,
					t
				]
			]), l = Io(l, cs(t.parser.constructs.insideSpan.null, e.slice(r + 1, n), t)), l = Io(l, [
				[
					"exit",
					a,
					t
				],
				[
					"enter",
					s,
					t
				],
				[
					"exit",
					s,
					t
				],
				[
					"exit",
					i,
					t
				]
			]), e[n][1].end.offset - e[n][1].start.offset ? (u = 2, l = Io(l, [[
				"enter",
				e[n][1],
				t
			], [
				"exit",
				e[n][1],
				t
			]])) : u = 0, Fo(e, r - 1, n - r + 3, l), n = r + l.length - u - 2;
			break;
		}
	}
	for (n = -1; ++n < e.length;) e[n][1].type === "attentionSequence" && (e[n][1].type = "data");
	return e;
}
function ds(e, t) {
	let n = this.parser.constructs.attentionMarkers.null, r = this.previous, i = ss(r), a;
	return o;
	function o(t) {
		return a = t, e.enter("attentionSequence"), s(t);
	}
	function s(o) {
		if (o === a) return e.consume(o), s;
		let c = e.exit("attentionSequence"), l = ss(o), u = !l || l === 2 && i || n.includes(o), d = !i || i === 2 && l || n.includes(r);
		return c._open = !!(a === 42 ? u : u && (i || !d)), c._close = !!(a === 42 ? d : d && (l || !u)), t(o);
	}
}
function fs(e, t) {
	e.column += t, e.offset += t, e._bufferIndex += t;
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/autolink.js
var ps = {
	name: "autolink",
	tokenize: ms
};
function ms(e, t, n) {
	let r = 0;
	return i;
	function i(t) {
		return e.enter("autolink"), e.enter("autolinkMarker"), e.consume(t), e.exit("autolinkMarker"), e.enter("autolinkProtocol"), a;
	}
	function a(t) {
		return Uo(t) ? (e.consume(t), o) : t === 64 ? n(t) : l(t);
	}
	function o(e) {
		return e === 43 || e === 45 || e === 46 || Wo(e) ? (r = 1, s(e)) : l(e);
	}
	function s(t) {
		return t === 58 ? (e.consume(t), r = 0, c) : (t === 43 || t === 45 || t === 46 || Wo(t)) && r++ < 32 ? (e.consume(t), s) : (r = 0, l(t));
	}
	function c(r) {
		return r === 62 ? (e.exit("autolinkProtocol"), e.enter("autolinkMarker"), e.consume(r), e.exit("autolinkMarker"), e.exit("autolink"), t) : r === null || r === 32 || r === 60 || Ko(r) ? n(r) : (e.consume(r), c);
	}
	function l(t) {
		return t === 64 ? (e.consume(t), u) : Go(t) ? (e.consume(t), l) : n(t);
	}
	function u(e) {
		return Wo(e) ? d(e) : n(e);
	}
	function d(n) {
		return n === 46 ? (e.consume(n), r = 0, u) : n === 62 ? (e.exit("autolinkProtocol").type = "autolinkEmail", e.enter("autolinkMarker"), e.consume(n), e.exit("autolinkMarker"), e.exit("autolink"), t) : f(n);
	}
	function f(t) {
		if ((t === 45 || Wo(t)) && r++ < 63) {
			let n = t === 45 ? f : d;
			return e.consume(t), n;
		}
		return n(t);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/blank-line.js
var hs = {
	partial: !0,
	tokenize: gs
};
function gs(e, t, n) {
	return r;
	function r(t) {
		return W(t) ? G(e, i, "linePrefix")(t) : i(t);
	}
	function i(e) {
		return e === null || U(e) ? t(e) : n(e);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/block-quote.js
var _s = {
	continuation: { tokenize: ys },
	exit: bs,
	name: "blockQuote",
	tokenize: vs
};
function vs(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		if (t === 62) {
			let n = r.containerState;
			return n.open ||= (e.enter("blockQuote", { _container: !0 }), !0), e.enter("blockQuotePrefix"), e.enter("blockQuoteMarker"), e.consume(t), e.exit("blockQuoteMarker"), a;
		}
		return n(t);
	}
	function a(n) {
		return W(n) ? (e.enter("blockQuotePrefixWhitespace"), e.consume(n), e.exit("blockQuotePrefixWhitespace"), e.exit("blockQuotePrefix"), t) : (e.exit("blockQuotePrefix"), t(n));
	}
}
function ys(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return W(t) ? G(e, a, "linePrefix", r.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4)(t) : a(t);
	}
	function a(r) {
		return e.attempt(_s, t, n)(r);
	}
}
function bs(e) {
	e.exit("blockQuote");
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/character-escape.js
var xs = {
	name: "characterEscape",
	tokenize: Ss
};
function Ss(e, t, n) {
	return r;
	function r(t) {
		return e.enter("characterEscape"), e.enter("escapeMarker"), e.consume(t), e.exit("escapeMarker"), i;
	}
	function i(r) {
		return Yo(r) ? (e.enter("characterEscapeValue"), e.consume(r), e.exit("characterEscapeValue"), e.exit("characterEscape"), t) : n(r);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/character-reference.js
var Cs = {
	name: "characterReference",
	tokenize: ws
};
function ws(e, t, n) {
	let r = this, i = 0, a, o;
	return s;
	function s(t) {
		return e.enter("characterReference"), e.enter("characterReferenceMarker"), e.consume(t), e.exit("characterReferenceMarker"), c;
	}
	function c(t) {
		return t === 35 ? (e.enter("characterReferenceMarkerNumeric"), e.consume(t), e.exit("characterReferenceMarkerNumeric"), l) : (e.enter("characterReferenceValue"), a = 31, o = Wo, u(t));
	}
	function l(t) {
		return t === 88 || t === 120 ? (e.enter("characterReferenceMarkerHexadecimal"), e.consume(t), e.exit("characterReferenceMarkerHexadecimal"), e.enter("characterReferenceValue"), a = 6, o = Jo, u) : (e.enter("characterReferenceValue"), a = 7, o = qo, u(t));
	}
	function u(s) {
		if (s === 59 && i) {
			let i = e.exit("characterReferenceValue");
			return o === Wo && !Po(r.sliceSerialize(i)) ? n(s) : (e.enter("characterReferenceMarker"), e.consume(s), e.exit("characterReferenceMarker"), e.exit("characterReference"), t);
		}
		return o(s) && i++ < a ? (e.consume(s), u) : n(s);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/code-fenced.js
var Ts = {
	partial: !0,
	tokenize: Os
}, Es = {
	concrete: !0,
	name: "codeFenced",
	tokenize: Ds
};
function Ds(e, t, n) {
	let r = this, i = {
		partial: !0,
		tokenize: x
	}, a = 0, o = 0, s;
	return c;
	function c(e) {
		return l(e);
	}
	function l(t) {
		let n = r.events[r.events.length - 1];
		return a = n && n[1].type === "linePrefix" ? n[2].sliceSerialize(n[1], !0).length : 0, s = t, e.enter("codeFenced"), e.enter("codeFencedFence"), e.enter("codeFencedFenceSequence"), u(t);
	}
	function u(t) {
		return t === s ? (o++, e.consume(t), u) : o < 3 ? n(t) : (e.exit("codeFencedFenceSequence"), W(t) ? G(e, d, "whitespace")(t) : d(t));
	}
	function d(n) {
		return n === null || U(n) ? (e.exit("codeFencedFence"), r.interrupt ? t(n) : e.check(Ts, h, b)(n)) : (e.enter("codeFencedFenceInfo"), e.enter("chunkString", { contentType: "string" }), f(n));
	}
	function f(t) {
		return t === null || U(t) ? (e.exit("chunkString"), e.exit("codeFencedFenceInfo"), d(t)) : W(t) ? (e.exit("chunkString"), e.exit("codeFencedFenceInfo"), G(e, p, "whitespace")(t)) : t === 96 && t === s ? n(t) : (e.consume(t), f);
	}
	function p(t) {
		return t === null || U(t) ? d(t) : (e.enter("codeFencedFenceMeta"), e.enter("chunkString", { contentType: "string" }), m(t));
	}
	function m(t) {
		return t === null || U(t) ? (e.exit("chunkString"), e.exit("codeFencedFenceMeta"), d(t)) : t === 96 && t === s ? n(t) : (e.consume(t), m);
	}
	function h(t) {
		return e.attempt(i, b, g)(t);
	}
	function g(t) {
		return e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), _;
	}
	function _(t) {
		return a > 0 && W(t) ? G(e, v, "linePrefix", a + 1)(t) : v(t);
	}
	function v(t) {
		return t === null || U(t) ? e.check(Ts, h, b)(t) : (e.enter("codeFlowValue"), y(t));
	}
	function y(t) {
		return t === null || U(t) ? (e.exit("codeFlowValue"), v(t)) : (e.consume(t), y);
	}
	function b(n) {
		return e.exit("codeFenced"), t(n);
	}
	function x(e, t, n) {
		let i = 0;
		return a;
		function a(t) {
			return e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), c;
		}
		function c(t) {
			return e.enter("codeFencedFence"), W(t) ? G(e, l, "linePrefix", r.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4)(t) : l(t);
		}
		function l(t) {
			return t === s ? (e.enter("codeFencedFenceSequence"), u(t)) : n(t);
		}
		function u(t) {
			return t === s ? (i++, e.consume(t), u) : i >= o ? (e.exit("codeFencedFenceSequence"), W(t) ? G(e, d, "whitespace")(t) : d(t)) : n(t);
		}
		function d(r) {
			return r === null || U(r) ? (e.exit("codeFencedFence"), t(r)) : n(r);
		}
	}
}
function Os(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return t === null ? n(t) : (e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), a);
	}
	function a(e) {
		return r.parser.lazy[r.now().line] ? n(e) : t(e);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/code-indented.js
var ks = {
	name: "codeIndented",
	tokenize: js
}, As = {
	partial: !0,
	tokenize: Ms
};
function js(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return e.enter("codeIndented"), G(e, a, "linePrefix", 5)(t);
	}
	function a(e) {
		let t = r.events[r.events.length - 1];
		return t && t[1].type === "linePrefix" && t[2].sliceSerialize(t[1], !0).length >= 4 ? o(e) : n(e);
	}
	function o(t) {
		return t === null ? c(t) : U(t) ? e.attempt(As, o, c)(t) : (e.enter("codeFlowValue"), s(t));
	}
	function s(t) {
		return t === null || U(t) ? (e.exit("codeFlowValue"), o(t)) : (e.consume(t), s);
	}
	function c(n) {
		return e.exit("codeIndented"), t(n);
	}
}
function Ms(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return r.parser.lazy[r.now().line] ? n(t) : U(t) ? (e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), i) : G(e, a, "linePrefix", 5)(t);
	}
	function a(e) {
		let a = r.events[r.events.length - 1];
		return a && a[1].type === "linePrefix" && a[2].sliceSerialize(a[1], !0).length >= 4 ? t(e) : U(e) ? i(e) : n(e);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/code-text.js
var Ns = {
	name: "codeText",
	previous: Fs,
	resolve: Ps,
	tokenize: Is
};
function Ps(e) {
	let t = e.length - 4, n = 3, r, i;
	if ((e[n][1].type === "lineEnding" || e[n][1].type === "space") && (e[t][1].type === "lineEnding" || e[t][1].type === "space")) {
		for (r = n; ++r < t;) if (e[r][1].type === "codeTextData") {
			e[n][1].type = "codeTextPadding", e[t][1].type = "codeTextPadding", n += 2, t -= 2;
			break;
		}
	}
	for (r = n - 1, t++; ++r <= t;) i === void 0 ? r !== t && e[r][1].type !== "lineEnding" && (i = r) : (r === t || e[r][1].type === "lineEnding") && (e[i][1].type = "codeTextData", r !== i + 2 && (e[i][1].end = e[r - 1][1].end, e.splice(i + 2, r - i - 2), t -= r - i - 2, r = i + 2), i = void 0);
	return e;
}
function Fs(e) {
	return e !== 96 || this.events[this.events.length - 1][1].type === "characterEscape";
}
function Is(e, t, n) {
	let r = 0, i, a;
	return o;
	function o(t) {
		return e.enter("codeText"), e.enter("codeTextSequence"), s(t);
	}
	function s(t) {
		return t === 96 ? (e.consume(t), r++, s) : (e.exit("codeTextSequence"), c(t));
	}
	function c(t) {
		return t === null ? n(t) : t === 32 ? (e.enter("space"), e.consume(t), e.exit("space"), c) : t === 96 ? (a = e.enter("codeTextSequence"), i = 0, u(t)) : U(t) ? (e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), c) : (e.enter("codeTextData"), l(t));
	}
	function l(t) {
		return t === null || t === 32 || t === 96 || U(t) ? (e.exit("codeTextData"), c(t)) : (e.consume(t), l);
	}
	function u(n) {
		return n === 96 ? (e.consume(n), i++, u) : i === r ? (e.exit("codeTextSequence"), e.exit("codeText"), t(n)) : (a.type = "codeTextData", l(n));
	}
}
//#endregion
//#region node_modules/micromark-util-subtokenize/lib/splice-buffer.js
var Ls = class {
	constructor(e) {
		this.left = e ? [...e] : [], this.right = [];
	}
	get(e) {
		if (e < 0 || e >= this.left.length + this.right.length) throw RangeError("Cannot access index `" + e + "` in a splice buffer of size `" + (this.left.length + this.right.length) + "`");
		return e < this.left.length ? this.left[e] : this.right[this.right.length - e + this.left.length - 1];
	}
	get length() {
		return this.left.length + this.right.length;
	}
	shift() {
		return this.setCursor(0), this.right.pop();
	}
	slice(e, t) {
		let n = t ?? Infinity;
		return n < this.left.length ? this.left.slice(e, n) : e > this.left.length ? this.right.slice(this.right.length - n + this.left.length, this.right.length - e + this.left.length).reverse() : this.left.slice(e).concat(this.right.slice(this.right.length - n + this.left.length).reverse());
	}
	splice(e, t, n) {
		let r = t || 0;
		this.setCursor(Math.trunc(e));
		let i = this.right.splice(this.right.length - r, Infinity);
		return n && Rs(this.left, n), i.reverse();
	}
	pop() {
		return this.setCursor(Infinity), this.left.pop();
	}
	push(e) {
		this.setCursor(Infinity), this.left.push(e);
	}
	pushMany(e) {
		this.setCursor(Infinity), Rs(this.left, e);
	}
	unshift(e) {
		this.setCursor(0), this.right.push(e);
	}
	unshiftMany(e) {
		this.setCursor(0), Rs(this.right, e.reverse());
	}
	setCursor(e) {
		if (!(e === this.left.length || e > this.left.length && this.right.length === 0 || e < 0 && this.left.length === 0)) if (e < this.left.length) {
			let t = this.left.splice(e, Infinity);
			Rs(this.right, t.reverse());
		} else {
			let t = this.right.splice(this.left.length + this.right.length - e, Infinity);
			Rs(this.left, t.reverse());
		}
	}
};
function Rs(e, t) {
	let n = 0;
	if (t.length < 1e4) e.push(...t);
	else for (; n < t.length;) e.push(...t.slice(n, n + 1e4)), n += 1e4;
}
//#endregion
//#region node_modules/micromark-util-subtokenize/index.js
function zs(e) {
	let t = {}, n = -1, r, i, a, o, s, c, l, u = new Ls(e);
	for (; ++n < u.length;) {
		for (; n in t;) n = t[n];
		if (r = u.get(n), n && r[1].type === "chunkFlow" && u.get(n - 1)[1].type === "listItemPrefix" && (c = r[1]._tokenizer.events, a = 0, a < c.length && c[a][1].type === "lineEndingBlank" && (a += 2), a < c.length && c[a][1].type === "content")) for (; ++a < c.length && c[a][1].type !== "content";) c[a][1].type === "chunkText" && (c[a][1]._isInFirstContentOfListItem = !0, a++);
		if (r[0] === "enter") r[1].contentType && (Object.assign(t, Bs(u, n)), n = t[n], l = !0);
		else if (r[1]._container) {
			for (a = n, i = void 0; a--;) if (o = u.get(a), o[1].type === "lineEnding" || o[1].type === "lineEndingBlank") o[0] === "enter" && (i && (u.get(i)[1].type = "lineEndingBlank"), o[1].type = "lineEnding", i = a);
			else if (!(o[1].type === "linePrefix" || o[1].type === "listItemIndent")) break;
			i && (r[1].end = { ...u.get(i)[1].start }, s = u.slice(i, n), s.unshift(r), u.splice(i, n - i + 1, s));
		}
	}
	return Fo(e, 0, Infinity, u.slice(0)), !l;
}
function Bs(e, t) {
	let n = e.get(t)[1], r = e.get(t)[2], i = t - 1, a = [], o = n._tokenizer;
	o || (o = r.parser[n.contentType](n.start), n._contentTypeTextTrailing && (o._contentTypeTextTrailing = !0));
	let s = o.events, c = [], l = {}, u, d, f = -1, p = n, m = 0, h = 0, g = [h];
	for (; p;) {
		for (; e.get(++i)[1] !== p;);
		a.push(i), p._tokenizer || (u = r.sliceStream(p), p.next || u.push(null), d && o.defineSkip(p.start), p._isInFirstContentOfListItem && (o._gfmTasklistFirstContentOfListItem = !0), o.write(u), p._isInFirstContentOfListItem && (o._gfmTasklistFirstContentOfListItem = void 0)), d = p, p = p.next;
	}
	for (p = n; ++f < s.length;) s[f][0] === "exit" && s[f - 1][0] === "enter" && s[f][1].type === s[f - 1][1].type && s[f][1].start.line !== s[f][1].end.line && (h = f + 1, g.push(h), p._tokenizer = void 0, p.previous = void 0, p = p.next);
	for (o.events = [], p ? (p._tokenizer = void 0, p.previous = void 0) : g.pop(), f = g.length; f--;) {
		let t = s.slice(g[f], g[f + 1]), n = a.pop();
		c.push([n, n + t.length - 1]), e.splice(n, 2, t);
	}
	for (c.reverse(), f = -1; ++f < c.length;) l[m + c[f][0]] = m + c[f][1], m += c[f][1] - c[f][0] - 1;
	return l;
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/content.js
var Vs = {
	resolve: Us,
	tokenize: Ws
}, Hs = {
	partial: !0,
	tokenize: Gs
};
function Us(e) {
	return zs(e), e;
}
function Ws(e, t) {
	let n;
	return r;
	function r(t) {
		return e.enter("content"), n = e.enter("chunkContent", { contentType: "content" }), i(t);
	}
	function i(t) {
		return t === null ? a(t) : U(t) ? e.check(Hs, o, a)(t) : (e.consume(t), i);
	}
	function a(n) {
		return e.exit("chunkContent"), e.exit("content"), t(n);
	}
	function o(t) {
		return e.consume(t), e.exit("chunkContent"), n.next = e.enter("chunkContent", {
			contentType: "content",
			previous: n
		}), n = n.next, i;
	}
}
function Gs(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return e.exit("chunkContent"), e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), G(e, a, "linePrefix");
	}
	function a(i) {
		if (i === null || U(i)) return n(i);
		let a = r.events[r.events.length - 1];
		return !r.parser.constructs.disable.null.includes("codeIndented") && a && a[1].type === "linePrefix" && a[2].sliceSerialize(a[1], !0).length >= 4 ? t(i) : e.interrupt(r.parser.constructs.flow, n, t)(i);
	}
}
//#endregion
//#region node_modules/micromark-factory-destination/index.js
function Ks(e, t, n, r, i, a, o, s, c) {
	let l = c || Infinity, u = 0;
	return d;
	function d(t) {
		return t === 60 ? (e.enter(r), e.enter(i), e.enter(a), e.consume(t), e.exit(a), f) : t === null || t === 32 || t === 41 || Ko(t) ? n(t) : (e.enter(r), e.enter(o), e.enter(s), e.enter("chunkString", { contentType: "string" }), h(t));
	}
	function f(n) {
		return n === 62 ? (e.enter(a), e.consume(n), e.exit(a), e.exit(i), e.exit(r), t) : (e.enter(s), e.enter("chunkString", { contentType: "string" }), p(n));
	}
	function p(t) {
		return t === 62 ? (e.exit("chunkString"), e.exit(s), f(t)) : t === null || t === 60 || U(t) ? n(t) : (e.consume(t), t === 92 ? m : p);
	}
	function m(t) {
		return t === 60 || t === 62 || t === 92 ? (e.consume(t), p) : p(t);
	}
	function h(i) {
		return !u && (i === null || i === 41 || Xo(i)) ? (e.exit("chunkString"), e.exit(s), e.exit(o), e.exit(r), t(i)) : u < l && i === 40 ? (e.consume(i), u++, h) : i === 41 ? (e.consume(i), u--, h) : i === null || i === 32 || i === 40 || Ko(i) ? n(i) : (e.consume(i), i === 92 ? g : h);
	}
	function g(t) {
		return t === 40 || t === 41 || t === 92 ? (e.consume(t), h) : h(t);
	}
}
//#endregion
//#region node_modules/micromark-factory-label/index.js
function qs(e, t, n, r, i, a) {
	let o = this, s = 0, c;
	return l;
	function l(t) {
		return e.enter(r), e.enter(i), e.consume(t), e.exit(i), e.enter(a), u;
	}
	function u(l) {
		return s > 999 || l === null || l === 91 || l === 93 && !c || l === 94 && !s && "_hiddenFootnoteSupport" in o.parser.constructs ? n(l) : l === 93 ? (e.exit(a), e.enter(i), e.consume(l), e.exit(i), e.exit(r), t) : U(l) ? (e.enter("lineEnding"), e.consume(l), e.exit("lineEnding"), u) : (e.enter("chunkString", { contentType: "string" }), d(l));
	}
	function d(t) {
		return t === null || t === 91 || t === 93 || U(t) || s++ > 999 ? (e.exit("chunkString"), u(t)) : (e.consume(t), c ||= !W(t), t === 92 ? f : d);
	}
	function f(t) {
		return t === 91 || t === 92 || t === 93 ? (e.consume(t), s++, d) : d(t);
	}
}
//#endregion
//#region node_modules/micromark-factory-title/index.js
function Js(e, t, n, r, i, a) {
	let o;
	return s;
	function s(t) {
		return t === 34 || t === 39 || t === 40 ? (e.enter(r), e.enter(i), e.consume(t), e.exit(i), o = t === 40 ? 41 : t, c) : n(t);
	}
	function c(n) {
		return n === o ? (e.enter(i), e.consume(n), e.exit(i), e.exit(r), t) : (e.enter(a), l(n));
	}
	function l(t) {
		return t === o ? (e.exit(a), c(o)) : t === null ? n(t) : U(t) ? (e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), G(e, l, "linePrefix")) : (e.enter("chunkString", { contentType: "string" }), u(t));
	}
	function u(t) {
		return t === o || t === null || U(t) ? (e.exit("chunkString"), l(t)) : (e.consume(t), t === 92 ? d : u);
	}
	function d(t) {
		return t === o || t === 92 ? (e.consume(t), u) : u(t);
	}
}
//#endregion
//#region node_modules/micromark-factory-whitespace/index.js
function Ys(e, t) {
	let n;
	return r;
	function r(i) {
		return U(i) ? (e.enter("lineEnding"), e.consume(i), e.exit("lineEnding"), n = !0, r) : W(i) ? G(e, r, n ? "linePrefix" : "lineSuffix")(i) : t(i);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/definition.js
var Xs = {
	name: "definition",
	tokenize: Qs
}, Zs = {
	partial: !0,
	tokenize: $s
};
function Qs(e, t, n) {
	let r = this, i;
	return a;
	function a(t) {
		return e.enter("definition"), o(t);
	}
	function o(t) {
		return qs.call(r, e, s, n, "definitionLabel", "definitionLabelMarker", "definitionLabelString")(t);
	}
	function s(t) {
		return i = Ho(r.sliceSerialize(r.events[r.events.length - 1][1]).slice(1, -1)), t === 58 ? (e.enter("definitionMarker"), e.consume(t), e.exit("definitionMarker"), c) : n(t);
	}
	function c(t) {
		return Xo(t) ? Ys(e, l)(t) : l(t);
	}
	function l(t) {
		return Ks(e, u, n, "definitionDestination", "definitionDestinationLiteral", "definitionDestinationLiteralMarker", "definitionDestinationRaw", "definitionDestinationString")(t);
	}
	function u(t) {
		return e.attempt(Zs, d, d)(t);
	}
	function d(t) {
		return W(t) ? G(e, f, "whitespace")(t) : f(t);
	}
	function f(a) {
		return a === null || U(a) ? (e.exit("definition"), r.parser.defined.push(i), t(a)) : n(a);
	}
}
function $s(e, t, n) {
	return r;
	function r(t) {
		return Xo(t) ? Ys(e, i)(t) : n(t);
	}
	function i(t) {
		return Js(e, a, n, "definitionTitle", "definitionTitleMarker", "definitionTitleString")(t);
	}
	function a(t) {
		return W(t) ? G(e, o, "whitespace")(t) : o(t);
	}
	function o(e) {
		return e === null || U(e) ? t(e) : n(e);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/hard-break-escape.js
var ec = {
	name: "hardBreakEscape",
	tokenize: tc
};
function tc(e, t, n) {
	return r;
	function r(t) {
		return e.enter("hardBreakEscape"), e.consume(t), i;
	}
	function i(r) {
		return U(r) ? (e.exit("hardBreakEscape"), t(r)) : n(r);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/heading-atx.js
var nc = {
	name: "headingAtx",
	resolve: rc,
	tokenize: ic
};
function rc(e, t) {
	let n = e.length - 2, r = 3, i, a;
	return e[r][1].type === "whitespace" && (r += 2), n - 2 > r && e[n][1].type === "whitespace" && (n -= 2), e[n][1].type === "atxHeadingSequence" && (r === n - 1 || n - 4 > r && e[n - 2][1].type === "whitespace") && (n -= r + 1 === n ? 2 : 4), n > r && (i = {
		type: "atxHeadingText",
		start: e[r][1].start,
		end: e[n][1].end
	}, a = {
		type: "chunkText",
		start: e[r][1].start,
		end: e[n][1].end,
		contentType: "text"
	}, Fo(e, r, n - r + 1, [
		[
			"enter",
			i,
			t
		],
		[
			"enter",
			a,
			t
		],
		[
			"exit",
			a,
			t
		],
		[
			"exit",
			i,
			t
		]
	])), e;
}
function ic(e, t, n) {
	let r = 0;
	return i;
	function i(t) {
		return e.enter("atxHeading"), a(t);
	}
	function a(t) {
		return e.enter("atxHeadingSequence"), o(t);
	}
	function o(t) {
		return t === 35 && r++ < 6 ? (e.consume(t), o) : t === null || Xo(t) ? (e.exit("atxHeadingSequence"), s(t)) : n(t);
	}
	function s(n) {
		return n === 35 ? (e.enter("atxHeadingSequence"), c(n)) : n === null || U(n) ? (e.exit("atxHeading"), t(n)) : W(n) ? G(e, s, "whitespace")(n) : (e.enter("atxHeadingText"), l(n));
	}
	function c(t) {
		return t === 35 ? (e.consume(t), c) : (e.exit("atxHeadingSequence"), s(t));
	}
	function l(t) {
		return t === null || t === 35 || Xo(t) ? (e.exit("atxHeadingText"), s(t)) : (e.consume(t), l);
	}
}
//#endregion
//#region node_modules/micromark-util-html-tag-name/index.js
var ac = /* @__PURE__ */ "address.article.aside.base.basefont.blockquote.body.caption.center.col.colgroup.dd.details.dialog.dir.div.dl.dt.fieldset.figcaption.figure.footer.form.frame.frameset.h1.h2.h3.h4.h5.h6.head.header.hr.html.iframe.legend.li.link.main.menu.menuitem.nav.noframes.ol.optgroup.option.p.param.search.section.summary.table.tbody.td.tfoot.th.thead.title.tr.track.ul".split("."), oc = [
	"pre",
	"script",
	"style",
	"textarea"
], sc = {
	concrete: !0,
	name: "htmlFlow",
	resolveTo: uc,
	tokenize: dc
}, cc = {
	partial: !0,
	tokenize: pc
}, lc = {
	partial: !0,
	tokenize: fc
};
function uc(e) {
	let t = e.length;
	for (; t-- && !(e[t][0] === "enter" && e[t][1].type === "htmlFlow"););
	return t > 1 && e[t - 2][1].type === "linePrefix" && (e[t][1].start = e[t - 2][1].start, e[t + 1][1].start = e[t - 2][1].start, e.splice(t - 2, 2)), e;
}
function dc(e, t, n) {
	let r = this, i, a, o, s, c;
	return l;
	function l(e) {
		return u(e);
	}
	function u(t) {
		return e.enter("htmlFlow"), e.enter("htmlFlowData"), e.consume(t), d;
	}
	function d(s) {
		return s === 33 ? (e.consume(s), f) : s === 47 ? (e.consume(s), a = !0, h) : s === 63 ? (e.consume(s), i = 3, r.interrupt ? t : te) : Uo(s) ? (e.consume(s), o = String.fromCharCode(s), g) : n(s);
	}
	function f(a) {
		return a === 45 ? (e.consume(a), i = 2, p) : a === 91 ? (e.consume(a), i = 5, s = 0, m) : Uo(a) ? (e.consume(a), i = 4, r.interrupt ? t : te) : n(a);
	}
	function p(i) {
		return i === 45 ? (e.consume(i), r.interrupt ? t : te) : n(i);
	}
	function m(i) {
		return i === "CDATA[".charCodeAt(s++) ? (e.consume(i), s === 6 ? r.interrupt ? t : O : m) : n(i);
	}
	function h(t) {
		return Uo(t) ? (e.consume(t), o = String.fromCharCode(t), g) : n(t);
	}
	function g(s) {
		if (s === null || s === 47 || s === 62 || Xo(s)) {
			let c = s === 47, l = o.toLowerCase();
			return !c && !a && oc.includes(l) ? (i = 1, r.interrupt ? t(s) : O(s)) : ac.includes(o.toLowerCase()) ? (i = 6, c ? (e.consume(s), _) : r.interrupt ? t(s) : O(s)) : (i = 7, r.interrupt && !r.parser.lazy[r.now().line] ? n(s) : a ? v(s) : y(s));
		}
		return s === 45 || Wo(s) ? (e.consume(s), o += String.fromCharCode(s), g) : n(s);
	}
	function _(i) {
		return i === 62 ? (e.consume(i), r.interrupt ? t : O) : n(i);
	}
	function v(t) {
		return W(t) ? (e.consume(t), v) : E(t);
	}
	function y(t) {
		return t === 47 ? (e.consume(t), E) : t === 58 || t === 95 || Uo(t) ? (e.consume(t), b) : W(t) ? (e.consume(t), y) : E(t);
	}
	function b(t) {
		return t === 45 || t === 46 || t === 58 || t === 95 || Wo(t) ? (e.consume(t), b) : x(t);
	}
	function x(t) {
		return t === 61 ? (e.consume(t), S) : W(t) ? (e.consume(t), x) : y(t);
	}
	function S(t) {
		return t === null || t === 60 || t === 61 || t === 62 || t === 96 ? n(t) : t === 34 || t === 39 ? (e.consume(t), c = t, C) : W(t) ? (e.consume(t), S) : w(t);
	}
	function C(t) {
		return t === c ? (e.consume(t), c = null, T) : t === null || U(t) ? n(t) : (e.consume(t), C);
	}
	function w(t) {
		return t === null || t === 34 || t === 39 || t === 47 || t === 60 || t === 61 || t === 62 || t === 96 || Xo(t) ? x(t) : (e.consume(t), w);
	}
	function T(e) {
		return e === 47 || e === 62 || W(e) ? y(e) : n(e);
	}
	function E(t) {
		return t === 62 ? (e.consume(t), D) : n(t);
	}
	function D(t) {
		return t === null || U(t) ? O(t) : W(t) ? (e.consume(t), D) : n(t);
	}
	function O(t) {
		return t === 45 && i === 2 ? (e.consume(t), j) : t === 60 && i === 1 ? (e.consume(t), M) : t === 62 && i === 4 ? (e.consume(t), ne) : t === 63 && i === 3 ? (e.consume(t), te) : t === 93 && i === 5 ? (e.consume(t), P) : U(t) && (i === 6 || i === 7) ? (e.exit("htmlFlowData"), e.check(cc, re, k)(t)) : t === null || U(t) ? (e.exit("htmlFlowData"), k(t)) : (e.consume(t), O);
	}
	function k(t) {
		return e.check(lc, ee, re)(t);
	}
	function ee(t) {
		return e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), A;
	}
	function A(t) {
		return t === null || U(t) ? k(t) : (e.enter("htmlFlowData"), O(t));
	}
	function j(t) {
		return t === 45 ? (e.consume(t), te) : O(t);
	}
	function M(t) {
		return t === 47 ? (e.consume(t), o = "", N) : O(t);
	}
	function N(t) {
		if (t === 62) {
			let n = o.toLowerCase();
			return oc.includes(n) ? (e.consume(t), ne) : O(t);
		}
		return Uo(t) && o.length < 8 ? (e.consume(t), o += String.fromCharCode(t), N) : O(t);
	}
	function P(t) {
		return t === 93 ? (e.consume(t), te) : O(t);
	}
	function te(t) {
		return t === 62 ? (e.consume(t), ne) : t === 45 && i === 2 ? (e.consume(t), te) : O(t);
	}
	function ne(t) {
		return t === null || U(t) ? (e.exit("htmlFlowData"), re(t)) : (e.consume(t), ne);
	}
	function re(n) {
		return e.exit("htmlFlow"), t(n);
	}
}
function fc(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return U(t) ? (e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), a) : n(t);
	}
	function a(e) {
		return r.parser.lazy[r.now().line] ? n(e) : t(e);
	}
}
function pc(e, t, n) {
	return r;
	function r(r) {
		return e.enter("lineEnding"), e.consume(r), e.exit("lineEnding"), e.attempt(hs, t, n);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/html-text.js
var mc = {
	name: "htmlText",
	tokenize: hc
};
function hc(e, t, n) {
	let r = this, i, a, o;
	return s;
	function s(t) {
		return e.enter("htmlText"), e.enter("htmlTextData"), e.consume(t), c;
	}
	function c(t) {
		return t === 33 ? (e.consume(t), l) : t === 47 ? (e.consume(t), x) : t === 63 ? (e.consume(t), y) : Uo(t) ? (e.consume(t), w) : n(t);
	}
	function l(t) {
		return t === 45 ? (e.consume(t), u) : t === 91 ? (e.consume(t), a = 0, m) : Uo(t) ? (e.consume(t), v) : n(t);
	}
	function u(t) {
		return t === 45 ? (e.consume(t), p) : n(t);
	}
	function d(t) {
		return t === null ? n(t) : t === 45 ? (e.consume(t), f) : U(t) ? (o = d, M(t)) : (e.consume(t), d);
	}
	function f(t) {
		return t === 45 ? (e.consume(t), p) : d(t);
	}
	function p(e) {
		return e === 62 ? j(e) : e === 45 ? f(e) : d(e);
	}
	function m(t) {
		return t === "CDATA[".charCodeAt(a++) ? (e.consume(t), a === 6 ? h : m) : n(t);
	}
	function h(t) {
		return t === null ? n(t) : t === 93 ? (e.consume(t), g) : U(t) ? (o = h, M(t)) : (e.consume(t), h);
	}
	function g(t) {
		return t === 93 ? (e.consume(t), _) : h(t);
	}
	function _(t) {
		return t === 62 ? j(t) : t === 93 ? (e.consume(t), _) : h(t);
	}
	function v(t) {
		return t === null || t === 62 ? j(t) : U(t) ? (o = v, M(t)) : (e.consume(t), v);
	}
	function y(t) {
		return t === null ? n(t) : t === 63 ? (e.consume(t), b) : U(t) ? (o = y, M(t)) : (e.consume(t), y);
	}
	function b(e) {
		return e === 62 ? j(e) : y(e);
	}
	function x(t) {
		return Uo(t) ? (e.consume(t), S) : n(t);
	}
	function S(t) {
		return t === 45 || Wo(t) ? (e.consume(t), S) : C(t);
	}
	function C(t) {
		return U(t) ? (o = C, M(t)) : W(t) ? (e.consume(t), C) : j(t);
	}
	function w(t) {
		return t === 45 || Wo(t) ? (e.consume(t), w) : t === 47 || t === 62 || Xo(t) ? T(t) : n(t);
	}
	function T(t) {
		return t === 47 ? (e.consume(t), j) : t === 58 || t === 95 || Uo(t) ? (e.consume(t), E) : U(t) ? (o = T, M(t)) : W(t) ? (e.consume(t), T) : j(t);
	}
	function E(t) {
		return t === 45 || t === 46 || t === 58 || t === 95 || Wo(t) ? (e.consume(t), E) : D(t);
	}
	function D(t) {
		return t === 61 ? (e.consume(t), O) : U(t) ? (o = D, M(t)) : W(t) ? (e.consume(t), D) : T(t);
	}
	function O(t) {
		return t === null || t === 60 || t === 61 || t === 62 || t === 96 ? n(t) : t === 34 || t === 39 ? (e.consume(t), i = t, k) : U(t) ? (o = O, M(t)) : W(t) ? (e.consume(t), O) : (e.consume(t), ee);
	}
	function k(t) {
		return t === i ? (e.consume(t), i = void 0, A) : t === null ? n(t) : U(t) ? (o = k, M(t)) : (e.consume(t), k);
	}
	function ee(t) {
		return t === null || t === 34 || t === 39 || t === 60 || t === 61 || t === 96 ? n(t) : t === 47 || t === 62 || Xo(t) ? T(t) : (e.consume(t), ee);
	}
	function A(e) {
		return e === 47 || e === 62 || Xo(e) ? T(e) : n(e);
	}
	function j(r) {
		return r === 62 ? (e.consume(r), e.exit("htmlTextData"), e.exit("htmlText"), t) : n(r);
	}
	function M(t) {
		return e.exit("htmlTextData"), e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), N;
	}
	function N(t) {
		return W(t) ? G(e, P, "linePrefix", r.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4)(t) : P(t);
	}
	function P(t) {
		return e.enter("htmlTextData"), o(t);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/label-end.js
var gc = {
	name: "labelEnd",
	resolveAll: bc,
	resolveTo: xc,
	tokenize: Sc
}, _c = { tokenize: Cc }, vc = { tokenize: wc }, yc = { tokenize: Tc };
function bc(e) {
	let t = -1, n = [];
	for (; ++t < e.length;) {
		let r = e[t][1];
		if (n.push(e[t]), r.type === "labelImage" || r.type === "labelLink" || r.type === "labelEnd") {
			let e = r.type === "labelImage" ? 4 : 2;
			r.type = "data", t += e;
		}
	}
	return e.length !== n.length && Fo(e, 0, e.length, n), e;
}
function xc(e, t) {
	let n = e.length, r = 0, i, a, o, s;
	for (; n--;) if (i = e[n][1], a) {
		if (i.type === "link" || i.type === "labelLink" && i._inactive) break;
		e[n][0] === "enter" && i.type === "labelLink" && (i._inactive = !0);
	} else if (o) {
		if (e[n][0] === "enter" && (i.type === "labelImage" || i.type === "labelLink") && !i._balanced && (a = n, i.type !== "labelLink")) {
			r = 2;
			break;
		}
	} else i.type === "labelEnd" && (o = n);
	let c = {
		type: e[a][1].type === "labelLink" ? "link" : "image",
		start: { ...e[a][1].start },
		end: { ...e[e.length - 1][1].end }
	}, l = {
		type: "label",
		start: { ...e[a][1].start },
		end: { ...e[o][1].end }
	}, u = {
		type: "labelText",
		start: { ...e[a + r + 2][1].end },
		end: { ...e[o - 2][1].start }
	};
	return s = [[
		"enter",
		c,
		t
	], [
		"enter",
		l,
		t
	]], s = Io(s, e.slice(a + 1, a + r + 3)), s = Io(s, [[
		"enter",
		u,
		t
	]]), s = Io(s, cs(t.parser.constructs.insideSpan.null, e.slice(a + r + 4, o - 3), t)), s = Io(s, [
		[
			"exit",
			u,
			t
		],
		e[o - 2],
		e[o - 1],
		[
			"exit",
			l,
			t
		]
	]), s = Io(s, e.slice(o + 1)), s = Io(s, [[
		"exit",
		c,
		t
	]]), Fo(e, a, e.length, s), e;
}
function Sc(e, t, n) {
	let r = this, i = r.events.length, a, o;
	for (; i--;) if ((r.events[i][1].type === "labelImage" || r.events[i][1].type === "labelLink") && !r.events[i][1]._balanced) {
		a = r.events[i][1];
		break;
	}
	return s;
	function s(t) {
		return a ? a._inactive ? d(t) : (o = r.parser.defined.includes(Ho(r.sliceSerialize({
			start: a.end,
			end: r.now()
		}))), e.enter("labelEnd"), e.enter("labelMarker"), e.consume(t), e.exit("labelMarker"), e.exit("labelEnd"), c) : n(t);
	}
	function c(t) {
		return t === 40 ? e.attempt(_c, u, o ? u : d)(t) : t === 91 ? e.attempt(vc, u, o ? l : d)(t) : o ? u(t) : d(t);
	}
	function l(t) {
		return e.attempt(yc, u, d)(t);
	}
	function u(e) {
		return t(e);
	}
	function d(e) {
		return a._balanced = !0, n(e);
	}
}
function Cc(e, t, n) {
	return r;
	function r(t) {
		return e.enter("resource"), e.enter("resourceMarker"), e.consume(t), e.exit("resourceMarker"), i;
	}
	function i(t) {
		return Xo(t) ? Ys(e, a)(t) : a(t);
	}
	function a(t) {
		return t === 41 ? u(t) : Ks(e, o, s, "resourceDestination", "resourceDestinationLiteral", "resourceDestinationLiteralMarker", "resourceDestinationRaw", "resourceDestinationString", 32)(t);
	}
	function o(t) {
		return Xo(t) ? Ys(e, c)(t) : u(t);
	}
	function s(e) {
		return n(e);
	}
	function c(t) {
		return t === 34 || t === 39 || t === 40 ? Js(e, l, n, "resourceTitle", "resourceTitleMarker", "resourceTitleString")(t) : u(t);
	}
	function l(t) {
		return Xo(t) ? Ys(e, u)(t) : u(t);
	}
	function u(r) {
		return r === 41 ? (e.enter("resourceMarker"), e.consume(r), e.exit("resourceMarker"), e.exit("resource"), t) : n(r);
	}
}
function wc(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return qs.call(r, e, a, o, "reference", "referenceMarker", "referenceString")(t);
	}
	function a(e) {
		return r.parser.defined.includes(Ho(r.sliceSerialize(r.events[r.events.length - 1][1]).slice(1, -1))) ? t(e) : n(e);
	}
	function o(e) {
		return n(e);
	}
}
function Tc(e, t, n) {
	return r;
	function r(t) {
		return e.enter("reference"), e.enter("referenceMarker"), e.consume(t), e.exit("referenceMarker"), i;
	}
	function i(r) {
		return r === 93 ? (e.enter("referenceMarker"), e.consume(r), e.exit("referenceMarker"), e.exit("reference"), t) : n(r);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/label-start-image.js
var Ec = {
	name: "labelStartImage",
	resolveAll: gc.resolveAll,
	tokenize: Dc
};
function Dc(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return e.enter("labelImage"), e.enter("labelImageMarker"), e.consume(t), e.exit("labelImageMarker"), a;
	}
	function a(t) {
		return t === 91 ? (e.enter("labelMarker"), e.consume(t), e.exit("labelMarker"), e.exit("labelImage"), o) : n(t);
	}
	function o(e) {
		/* c8 ignore next 3 */
		return e === 94 && "_hiddenFootnoteSupport" in r.parser.constructs ? n(e) : t(e);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/label-start-link.js
var Oc = {
	name: "labelStartLink",
	resolveAll: gc.resolveAll,
	tokenize: kc
};
function kc(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return e.enter("labelLink"), e.enter("labelMarker"), e.consume(t), e.exit("labelMarker"), e.exit("labelLink"), a;
	}
	function a(e) {
		/* c8 ignore next 3 */
		return e === 94 && "_hiddenFootnoteSupport" in r.parser.constructs ? n(e) : t(e);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/line-ending.js
var Ac = {
	name: "lineEnding",
	tokenize: jc
};
function jc(e, t) {
	return n;
	function n(n) {
		return e.enter("lineEnding"), e.consume(n), e.exit("lineEnding"), G(e, t, "linePrefix");
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/thematic-break.js
var Mc = {
	name: "thematicBreak",
	tokenize: Nc
};
function Nc(e, t, n) {
	let r = 0, i;
	return a;
	function a(t) {
		return e.enter("thematicBreak"), o(t);
	}
	function o(e) {
		return i = e, s(e);
	}
	function s(a) {
		return a === i ? (e.enter("thematicBreakSequence"), c(a)) : r >= 3 && (a === null || U(a)) ? (e.exit("thematicBreak"), t(a)) : n(a);
	}
	function c(t) {
		return t === i ? (e.consume(t), r++, c) : (e.exit("thematicBreakSequence"), W(t) ? G(e, s, "whitespace")(t) : s(t));
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/list.js
var Pc = {
	continuation: { tokenize: Rc },
	exit: Bc,
	name: "list",
	tokenize: Lc
}, Fc = {
	partial: !0,
	tokenize: Vc
}, Ic = {
	partial: !0,
	tokenize: zc
};
function Lc(e, t, n) {
	let r = this, i = r.events[r.events.length - 1], a = i && i[1].type === "linePrefix" ? i[2].sliceSerialize(i[1], !0).length : 0, o = 0;
	return s;
	function s(t) {
		let i = r.containerState.type || (t === 42 || t === 43 || t === 45 ? "listUnordered" : "listOrdered");
		if (i === "listUnordered" ? !r.containerState.marker || t === r.containerState.marker : qo(t)) {
			if (r.containerState.type || (r.containerState.type = i, e.enter(i, { _container: !0 })), i === "listUnordered") return e.enter("listItemPrefix"), t === 42 || t === 45 ? e.check(Mc, n, l)(t) : l(t);
			if (!r.interrupt || t === 49) return e.enter("listItemPrefix"), e.enter("listItemValue"), c(t);
		}
		return n(t);
	}
	function c(t) {
		return qo(t) && ++o < 10 ? (e.consume(t), c) : (!r.interrupt || o < 2) && (r.containerState.marker ? t === r.containerState.marker : t === 41 || t === 46) ? (e.exit("listItemValue"), l(t)) : n(t);
	}
	function l(t) {
		return e.enter("listItemMarker"), e.consume(t), e.exit("listItemMarker"), r.containerState.marker = r.containerState.marker || t, e.check(hs, r.interrupt ? n : u, e.attempt(Fc, f, d));
	}
	function u(e) {
		return r.containerState.initialBlankLine = !0, a++, f(e);
	}
	function d(t) {
		return W(t) ? (e.enter("listItemPrefixWhitespace"), e.consume(t), e.exit("listItemPrefixWhitespace"), f) : n(t);
	}
	function f(n) {
		return r.containerState.size = a + r.sliceSerialize(e.exit("listItemPrefix"), !0).length, t(n);
	}
}
function Rc(e, t, n) {
	let r = this;
	return r.containerState._closeFlow = void 0, e.check(hs, i, a);
	function i(n) {
		return r.containerState.furtherBlankLines = r.containerState.furtherBlankLines || r.containerState.initialBlankLine, G(e, t, "listItemIndent", r.containerState.size + 1)(n);
	}
	function a(n) {
		return r.containerState.furtherBlankLines || !W(n) ? (r.containerState.furtherBlankLines = void 0, r.containerState.initialBlankLine = void 0, o(n)) : (r.containerState.furtherBlankLines = void 0, r.containerState.initialBlankLine = void 0, e.attempt(Ic, t, o)(n));
	}
	function o(i) {
		return r.containerState._closeFlow = !0, r.interrupt = void 0, G(e, e.attempt(Pc, t, n), "linePrefix", r.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4)(i);
	}
}
function zc(e, t, n) {
	let r = this;
	return G(e, i, "listItemIndent", r.containerState.size + 1);
	function i(e) {
		let i = r.events[r.events.length - 1];
		return i && i[1].type === "listItemIndent" && i[2].sliceSerialize(i[1], !0).length === r.containerState.size ? t(e) : n(e);
	}
}
function Bc(e) {
	e.exit(this.containerState.type);
}
function Vc(e, t, n) {
	let r = this;
	return G(e, i, "listItemPrefixWhitespace", r.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 5);
	function i(e) {
		let i = r.events[r.events.length - 1];
		return !W(e) && i && i[1].type === "listItemPrefixWhitespace" ? t(e) : n(e);
	}
}
//#endregion
//#region node_modules/micromark-core-commonmark/lib/setext-underline.js
var Hc = {
	name: "setextUnderline",
	resolveTo: Uc,
	tokenize: Wc
};
function Uc(e, t) {
	let n = e.length, r, i, a;
	for (; n--;) if (e[n][0] === "enter") {
		if (e[n][1].type === "content") {
			r = n;
			break;
		}
		e[n][1].type === "paragraph" && (i = n);
	} else e[n][1].type === "content" && e.splice(n, 1), !a && e[n][1].type === "definition" && (a = n);
	let o = {
		type: "setextHeading",
		start: { ...e[r][1].start },
		end: { ...e[e.length - 1][1].end }
	};
	return e[i][1].type = "setextHeadingText", a ? (e.splice(i, 0, [
		"enter",
		o,
		t
	]), e.splice(a + 1, 0, [
		"exit",
		e[r][1],
		t
	]), e[r][1].end = { ...e[a][1].end }) : e[r][1] = o, e.push([
		"exit",
		o,
		t
	]), e;
}
function Wc(e, t, n) {
	let r = this, i;
	return a;
	function a(t) {
		let a = r.events.length, s;
		for (; a--;) if (r.events[a][1].type !== "lineEnding" && r.events[a][1].type !== "linePrefix" && r.events[a][1].type !== "content") {
			s = r.events[a][1].type === "paragraph";
			break;
		}
		return !r.parser.lazy[r.now().line] && (r.interrupt || s) ? (e.enter("setextHeadingLine"), i = t, o(t)) : n(t);
	}
	function o(t) {
		return e.enter("setextHeadingLineSequence"), s(t);
	}
	function s(t) {
		return t === i ? (e.consume(t), s) : (e.exit("setextHeadingLineSequence"), W(t) ? G(e, c, "lineSuffix")(t) : c(t));
	}
	function c(r) {
		return r === null || U(r) ? (e.exit("setextHeadingLine"), t(r)) : n(r);
	}
}
//#endregion
//#region node_modules/micromark/lib/initialize/flow.js
var Gc = { tokenize: Kc };
function Kc(e) {
	let t = this, n = e.attempt(hs, r, e.attempt(this.parser.constructs.flowInitial, i, G(e, e.attempt(this.parser.constructs.flow, i, e.attempt(Vs, i)), "linePrefix")));
	return n;
	function r(r) {
		if (r === null) {
			e.consume(r);
			return;
		}
		return e.enter("lineEndingBlank"), e.consume(r), e.exit("lineEndingBlank"), t.currentConstruct = void 0, n;
	}
	function i(r) {
		if (r === null) {
			e.consume(r);
			return;
		}
		return e.enter("lineEnding"), e.consume(r), e.exit("lineEnding"), t.currentConstruct = void 0, n;
	}
}
//#endregion
//#region node_modules/micromark/lib/initialize/text.js
var qc = { resolveAll: Zc() }, Jc = Xc("string"), Yc = Xc("text");
function Xc(e) {
	return {
		resolveAll: Zc(e === "text" ? Qc : void 0),
		tokenize: t
	};
	function t(t) {
		let n = this, r = this.parser.constructs[e], i = t.attempt(r, a, o);
		return a;
		function a(e) {
			return c(e) ? i(e) : o(e);
		}
		function o(e) {
			if (e === null) {
				t.consume(e);
				return;
			}
			return t.enter("data"), t.consume(e), s;
		}
		function s(e) {
			return c(e) ? (t.exit("data"), i(e)) : (t.consume(e), s);
		}
		function c(e) {
			if (e === null) return !0;
			let t = r[e], i = -1;
			if (t) for (; ++i < t.length;) {
				let e = t[i];
				if (!e.previous || e.previous.call(n, n.previous)) return !0;
			}
			return !1;
		}
	}
}
function Zc(e) {
	return t;
	function t(t, n) {
		let r = -1, i;
		for (; ++r <= t.length;) i === void 0 ? t[r] && t[r][1].type === "data" && (i = r, r++) : (!t[r] || t[r][1].type !== "data") && (r !== i + 2 && (t[i][1].end = t[r - 1][1].end, t.splice(i + 2, r - i - 2), r = i + 2), i = void 0);
		return e ? e(t, n) : t;
	}
}
function Qc(e, t) {
	let n = 0;
	for (; ++n <= e.length;) if ((n === e.length || e[n][1].type === "lineEnding") && e[n - 1][1].type === "data") {
		let r = e[n - 1][1], i = t.sliceStream(r), a = i.length, o = -1, s = 0, c;
		for (; a--;) {
			let e = i[a];
			if (typeof e == "string") {
				for (o = e.length; e.charCodeAt(o - 1) === 32;) s++, o--;
				if (o) break;
				o = -1;
			} else if (e === -2) c = !0, s++;
			else if (e !== -1) {
				a++;
				break;
			}
		}
		if (t._contentTypeTextTrailing && n === e.length && (s = 0), s) {
			let i = {
				type: n === e.length || c || s < 2 ? "lineSuffix" : "hardBreakTrailing",
				start: {
					_bufferIndex: a ? o : r.start._bufferIndex + o,
					_index: r.start._index + a,
					line: r.end.line,
					column: r.end.column - s,
					offset: r.end.offset - s
				},
				end: { ...r.end }
			};
			r.end = { ...i.start }, r.start.offset === r.end.offset ? Object.assign(r, i) : (e.splice(n, 0, [
				"enter",
				i,
				t
			], [
				"exit",
				i,
				t
			]), n += 2);
		}
		n++;
	}
	return e;
}
//#endregion
//#region node_modules/micromark/lib/constructs.js
var $c = /* @__PURE__ */ t({
	attentionMarkers: () => sl,
	contentInitial: () => tl,
	disable: () => cl,
	document: () => el,
	flow: () => rl,
	flowInitial: () => nl,
	insideSpan: () => ol,
	string: () => il,
	text: () => al
}), el = {
	42: Pc,
	43: Pc,
	45: Pc,
	48: Pc,
	49: Pc,
	50: Pc,
	51: Pc,
	52: Pc,
	53: Pc,
	54: Pc,
	55: Pc,
	56: Pc,
	57: Pc,
	62: _s
}, tl = { 91: Xs }, nl = {
	[-2]: ks,
	[-1]: ks,
	32: ks
}, rl = {
	35: nc,
	42: Mc,
	45: [Hc, Mc],
	60: sc,
	61: Hc,
	95: Mc,
	96: Es,
	126: Es
}, il = {
	38: Cs,
	92: xs
}, al = {
	[-5]: Ac,
	[-4]: Ac,
	[-3]: Ac,
	33: Ec,
	38: Cs,
	42: ls,
	60: [ps, mc],
	91: Oc,
	92: [ec, xs],
	93: gc,
	95: ls,
	96: Ns
}, ol = { null: [ls, qc] }, sl = { null: [42, 95] }, cl = { null: [] };
//#endregion
//#region node_modules/micromark/lib/create-tokenizer.js
function ll(e, t, n) {
	let r = {
		_bufferIndex: -1,
		_index: 0,
		line: n && n.line || 1,
		column: n && n.column || 1,
		offset: n && n.offset || 0
	}, i = {}, a = [], o = [], s = [], c = {
		attempt: C(x),
		check: C(S),
		consume: v,
		enter: y,
		exit: b,
		interrupt: C(S, { interrupt: !0 })
	}, l = {
		code: null,
		containerState: {},
		defineSkip: h,
		events: [],
		now: m,
		parser: e,
		previous: null,
		sliceSerialize: f,
		sliceStream: p,
		write: d
	}, u = t.tokenize.call(l, c);
	return t.resolveAll && a.push(t), l;
	function d(e) {
		return o = Io(o, e), g(), o[o.length - 1] === null ? (w(t, 0), l.events = cs(a, l.events, l), l.events) : [];
	}
	function f(e, t) {
		return dl(p(e), t);
	}
	function p(e) {
		return ul(o, e);
	}
	function m() {
		let { _bufferIndex: e, _index: t, line: n, column: i, offset: a } = r;
		return {
			_bufferIndex: e,
			_index: t,
			line: n,
			column: i,
			offset: a
		};
	}
	function h(e) {
		i[e.line] = e.column, E();
	}
	function g() {
		let e;
		for (; r._index < o.length;) {
			let t = o[r._index];
			if (typeof t == "string") for (e = r._index, r._bufferIndex < 0 && (r._bufferIndex = 0); r._index === e && r._bufferIndex < t.length;) _(t.charCodeAt(r._bufferIndex));
			else _(t);
		}
	}
	function _(e) {
		u = u(e);
	}
	function v(e) {
		U(e) ? (r.line++, r.column = 1, r.offset += e === -3 ? 2 : 1, E()) : e !== -1 && (r.column++, r.offset++), r._bufferIndex < 0 ? r._index++ : (r._bufferIndex++, r._bufferIndex === o[r._index].length && (r._bufferIndex = -1, r._index++)), l.previous = e;
	}
	function y(e, t) {
		let n = t || {};
		return n.type = e, n.start = m(), l.events.push([
			"enter",
			n,
			l
		]), s.push(n), n;
	}
	function b(e) {
		let t = s.pop();
		return t.end = m(), l.events.push([
			"exit",
			t,
			l
		]), t;
	}
	function x(e, t) {
		w(e, t.from);
	}
	function S(e, t) {
		t.restore();
	}
	function C(e, t) {
		return n;
		function n(n, r, i) {
			let a, o, s, u;
			return Array.isArray(n) ? f(n) : "tokenize" in n ? f([n]) : d(n);
			function d(e) {
				return t;
				function t(t) {
					let n = t !== null && e[t], r = t !== null && e.null;
					return f([...Array.isArray(n) ? n : n ? [n] : [], ...Array.isArray(r) ? r : r ? [r] : []])(t);
				}
			}
			function f(e) {
				return a = e, o = 0, e.length === 0 ? i : p(e[o]);
			}
			function p(e) {
				return n;
				function n(n) {
					return u = T(), s = e, e.partial || (l.currentConstruct = e), e.name && l.parser.constructs.disable.null.includes(e.name) ? h(n) : e.tokenize.call(t ? Object.assign(Object.create(l), t) : l, c, m, h)(n);
				}
			}
			function m(t) {
				return e(s, u), r;
			}
			function h(e) {
				return u.restore(), ++o < a.length ? p(a[o]) : i;
			}
		}
	}
	function w(e, t) {
		e.resolveAll && !a.includes(e) && a.push(e), e.resolve && Fo(l.events, t, l.events.length - t, e.resolve(l.events.slice(t), l)), e.resolveTo && (l.events = e.resolveTo(l.events, l));
	}
	function T() {
		let e = m(), t = l.previous, n = l.currentConstruct, i = l.events.length, a = Array.from(s);
		return {
			from: i,
			restore: o
		};
		function o() {
			r = e, l.previous = t, l.currentConstruct = n, l.events.length = i, s = a, E();
		}
	}
	function E() {
		r.line in i && r.column < 2 && (r.column = i[r.line], r.offset += i[r.line] - 1);
	}
}
function ul(e, t) {
	let n = t.start._index, r = t.start._bufferIndex, i = t.end._index, a = t.end._bufferIndex, o;
	if (n === i) o = [e[n].slice(r, a)];
	else {
		if (o = e.slice(n, i), r > -1) {
			let e = o[0];
			typeof e == "string" ? o[0] = e.slice(r) : o.shift();
		}
		a > 0 && o.push(e[i].slice(0, a));
	}
	return o;
}
function dl(e, t) {
	let n = -1, r = [], i;
	for (; ++n < e.length;) {
		let a = e[n], o;
		if (typeof a == "string") o = a;
		else switch (a) {
			case -5:
				o = "\r";
				break;
			case -4:
				o = "\n";
				break;
			case -3:
				o = "\r\n";
				break;
			case -2:
				o = t ? " " : "	";
				break;
			case -1:
				if (!t && i) continue;
				o = " ";
				break;
			default: o = String.fromCharCode(a);
		}
		i = a === -2, r.push(o);
	}
	return r.join("");
}
//#endregion
//#region node_modules/micromark/lib/parse.js
function fl(e) {
	let t = {
		constructs: Ro([$c, ...(e || {}).extensions || []]),
		content: n(ts),
		defined: [],
		document: n(rs),
		flow: n(Gc),
		lazy: {},
		string: n(Jc),
		text: n(Yc)
	};
	return t;
	function n(e) {
		return n;
		function n(n) {
			return ll(t, e, n);
		}
	}
}
//#endregion
//#region node_modules/micromark/lib/postprocess.js
function pl(e) {
	for (; !zs(e););
	return e;
}
//#endregion
//#region node_modules/micromark/lib/preprocess.js
var ml = /[\0\t\n\r]/g;
function hl() {
	let e = 1, t = "", n = !0, r;
	return i;
	function i(i, a, o) {
		let s = [], c, l, u, d, f;
		for (i = t + (typeof i == "string" ? i.toString() : new TextDecoder(a || void 0).decode(i)), u = 0, t = "", n &&= (i.charCodeAt(0) === 65279 && u++, void 0); u < i.length;) {
			if (ml.lastIndex = u, c = ml.exec(i), d = c && c.index !== void 0 ? c.index : i.length, f = i.charCodeAt(d), !c) {
				t = i.slice(u);
				break;
			}
			if (f === 10 && u === d && r) s.push(-3), r = void 0;
			else switch (r &&= (s.push(-5), void 0), u < d && (s.push(i.slice(u, d)), e += d - u), f) {
				case 0:
					s.push(65533), e++;
					break;
				case 9:
					for (l = Math.ceil(e / 4) * 4, s.push(-2); e++ < l;) s.push(-1);
					break;
				case 10:
					s.push(-4), e = 1;
					break;
				default: r = !0, e = 1;
			}
			u = d + 1;
		}
		return o && (r && s.push(-5), t && s.push(t), s.push(null)), s;
	}
}
//#endregion
//#region node_modules/micromark-util-decode-string/index.js
var gl = /\\([!-/:-@[-`{-~])|&(#(?:\d{1,7}|x[\da-f]{1,6})|[\da-z]{1,31});/gi;
function _l(e) {
	return e.replace(gl, vl);
}
function vl(e, t, n) {
	if (t) return t;
	if (n.charCodeAt(0) === 35) {
		let e = n.charCodeAt(1), t = e === 120 || e === 88;
		return Vo(n.slice(t ? 2 : 1), t ? 16 : 10);
	}
	return Po(n) || e;
}
//#endregion
//#region node_modules/mdast-util-from-markdown/lib/index.js
var yl = {}.hasOwnProperty;
function bl(e, t, n) {
	return t && typeof t == "object" && (n = t, t = void 0), xl(n)(pl(fl(n).document().write(hl()(e, t, !0))));
}
function xl(e) {
	let t = {
		transforms: [],
		canContainEols: [
			"emphasis",
			"fragment",
			"heading",
			"paragraph",
			"strong"
		],
		enter: {
			autolink: a(ve),
			autolinkProtocol: T,
			autolinkEmail: T,
			atxHeading: a(he),
			blockQuote: a(ue),
			characterEscape: T,
			characterReference: T,
			codeFenced: a(de),
			codeFencedFenceInfo: o,
			codeFencedFenceMeta: o,
			codeIndented: a(de, o),
			codeText: a(fe, o),
			codeTextData: T,
			data: T,
			codeFlowValue: T,
			definition: a(pe),
			definitionDestinationString: o,
			definitionLabelString: o,
			definitionTitleString: o,
			emphasis: a(me),
			hardBreakEscape: a(I),
			hardBreakTrailing: a(I),
			htmlFlow: a(ge, o),
			htmlFlowData: T,
			htmlText: a(ge, o),
			htmlTextData: T,
			image: a(_e),
			label: o,
			link: a(ve),
			listItem: a(be),
			listItemValue: f,
			listOrdered: a(ye, d),
			listUnordered: a(ye),
			paragraph: a(xe),
			reference: ie,
			referenceString: o,
			resourceDestinationString: o,
			resourceTitleString: o,
			setextHeading: a(he),
			strong: a(L),
			thematicBreak: a(Ce)
		},
		exit: {
			atxHeading: c(),
			atxHeadingSequence: x,
			autolink: c(),
			autolinkEmail: le,
			autolinkProtocol: ce,
			blockQuote: c(),
			characterEscapeValue: E,
			characterReferenceMarkerHexadecimal: ae,
			characterReferenceMarkerNumeric: ae,
			characterReferenceValue: oe,
			characterReference: se,
			codeFenced: c(g),
			codeFencedFence: h,
			codeFencedFenceInfo: p,
			codeFencedFenceMeta: m,
			codeFlowValue: E,
			codeIndented: c(_),
			codeText: c(A),
			codeTextData: E,
			data: E,
			definition: c(),
			definitionDestinationString: b,
			definitionLabelString: v,
			definitionTitleString: y,
			emphasis: c(),
			hardBreakEscape: c(O),
			hardBreakTrailing: c(O),
			htmlFlow: c(k),
			htmlFlowData: E,
			htmlText: c(ee),
			htmlTextData: E,
			image: c(M),
			label: P,
			labelText: N,
			lineEnding: D,
			link: c(j),
			listItem: c(),
			listOrdered: c(),
			listUnordered: c(),
			paragraph: c(),
			referenceString: F,
			resourceDestinationString: te,
			resourceTitleString: ne,
			resource: re,
			setextHeading: c(w),
			setextHeadingLineSequence: C,
			setextHeadingText: S,
			strong: c(),
			thematicBreak: c()
		}
	};
	Cl(t, (e || {}).mdastExtensions || []);
	let n = {};
	return r;
	function r(e) {
		let r = {
			type: "root",
			children: []
		}, a = {
			stack: [r],
			tokenStack: [],
			config: t,
			enter: s,
			exit: l,
			buffer: o,
			resume: u,
			data: n
		}, c = [], d = -1;
		for (; ++d < e.length;) (e[d][1].type === "listOrdered" || e[d][1].type === "listUnordered") && (e[d][0] === "enter" ? c.push(d) : d = i(e, c.pop(), d));
		for (d = -1; ++d < e.length;) {
			let n = t[e[d][0]];
			yl.call(n, e[d][1].type) && n[e[d][1].type].call(Object.assign({ sliceSerialize: e[d][2].sliceSerialize }, a), e[d][1]);
		}
		if (a.tokenStack.length > 0) {
			let e = a.tokenStack[a.tokenStack.length - 1];
			(e[1] || Tl).call(a, void 0, e[0]);
		}
		for (r.position = {
			start: Sl(e.length > 0 ? e[0][1].start : {
				line: 1,
				column: 1,
				offset: 0
			}),
			end: Sl(e.length > 0 ? e[e.length - 2][1].end : {
				line: 1,
				column: 1,
				offset: 0
			})
		}, d = -1; ++d < t.transforms.length;) r = t.transforms[d](r) || r;
		return r;
	}
	function i(e, t, n) {
		let r = t - 1, i = -1, a = !1, o, s, c, l;
		for (; ++r <= n;) {
			let t = e[r];
			switch (t[1].type) {
				case "listUnordered":
				case "listOrdered":
				case "blockQuote":
					t[0] === "enter" ? i++ : i--, l = void 0;
					break;
				case "lineEndingBlank":
					t[0] === "enter" && (o && !l && !i && !c && (c = r), l = void 0);
					break;
				case "linePrefix":
				case "listItemValue":
				case "listItemMarker":
				case "listItemPrefix":
				case "listItemPrefixWhitespace": break;
				default: l = void 0;
			}
			if (!i && t[0] === "enter" && t[1].type === "listItemPrefix" || i === -1 && t[0] === "exit" && (t[1].type === "listUnordered" || t[1].type === "listOrdered")) {
				if (o) {
					let i = r;
					for (s = void 0; i--;) {
						let t = e[i];
						if (t[1].type === "lineEnding" || t[1].type === "lineEndingBlank") {
							if (t[0] === "exit") continue;
							s && (e[s][1].type = "lineEndingBlank", a = !0), t[1].type = "lineEnding", s = i;
						} else if (!(t[1].type === "linePrefix" || t[1].type === "blockQuotePrefix" || t[1].type === "blockQuotePrefixWhitespace" || t[1].type === "blockQuoteMarker" || t[1].type === "listItemIndent")) break;
					}
					c && (!s || c < s) && (o._spread = !0), o.end = Object.assign({}, s ? e[s][1].start : t[1].end), e.splice(s || r, 0, [
						"exit",
						o,
						t[2]
					]), r++, n++;
				}
				if (t[1].type === "listItemPrefix") {
					let i = {
						type: "listItem",
						_spread: !1,
						start: Object.assign({}, t[1].start),
						end: void 0
					};
					o = i, e.splice(r, 0, [
						"enter",
						i,
						t[2]
					]), r++, n++, c = void 0, l = !0;
				}
			}
		}
		return e[t][1]._spread = a, n;
	}
	function a(e, t) {
		return n;
		function n(n) {
			s.call(this, e(n), n), t && t.call(this, n);
		}
	}
	function o() {
		this.stack.push({
			type: "fragment",
			children: []
		});
	}
	function s(e, t, n) {
		this.stack[this.stack.length - 1].children.push(e), this.stack.push(e), this.tokenStack.push([t, n || void 0]), e.position = {
			start: Sl(t.start),
			end: void 0
		};
	}
	function c(e) {
		return t;
		function t(t) {
			e && e.call(this, t), l.call(this, t);
		}
	}
	function l(e, t) {
		let n = this.stack.pop(), r = this.tokenStack.pop();
		if (r) r[0].type !== e.type && (t ? t.call(this, e, r[0]) : (r[1] || Tl).call(this, e, r[0]));
		else throw Error("Cannot close `" + e.type + "` (" + Ka({
			start: e.start,
			end: e.end
		}) + "): it’s not open");
		n.position.end = Sl(e.end);
	}
	function u() {
		return ko(this.stack.pop());
	}
	function d() {
		this.data.expectingFirstListItemValue = !0;
	}
	function f(e) {
		if (this.data.expectingFirstListItemValue) {
			let t = this.stack[this.stack.length - 2];
			t.start = Number.parseInt(this.sliceSerialize(e), 10), this.data.expectingFirstListItemValue = void 0;
		}
	}
	function p() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.lang = e;
	}
	function m() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.meta = e;
	}
	function h() {
		this.data.flowCodeInside || (this.buffer(), this.data.flowCodeInside = !0);
	}
	function g() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.value = e.replace(/^(\r?\n|\r)|(\r?\n|\r)$/g, ""), this.data.flowCodeInside = void 0;
	}
	function _() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.value = e.replace(/(\r?\n|\r)$/g, "");
	}
	function v(e) {
		let t = this.resume(), n = this.stack[this.stack.length - 1];
		n.label = t, n.identifier = Ho(this.sliceSerialize(e)).toLowerCase();
	}
	function y() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.title = e;
	}
	function b() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.url = e;
	}
	function x(e) {
		let t = this.stack[this.stack.length - 1];
		t.depth ||= this.sliceSerialize(e).length;
	}
	function S() {
		this.data.setextHeadingSlurpLineEnding = !0;
	}
	function C(e) {
		let t = this.stack[this.stack.length - 1];
		t.depth = this.sliceSerialize(e).codePointAt(0) === 61 ? 1 : 2;
	}
	function w() {
		this.data.setextHeadingSlurpLineEnding = void 0;
	}
	function T(e) {
		let t = this.stack[this.stack.length - 1].children, n = t[t.length - 1];
		(!n || n.type !== "text") && (n = Se(), n.position = {
			start: Sl(e.start),
			end: void 0
		}, t.push(n)), this.stack.push(n);
	}
	function E(e) {
		let t = this.stack.pop();
		t.value += this.sliceSerialize(e), t.position.end = Sl(e.end);
	}
	function D(e) {
		let n = this.stack[this.stack.length - 1];
		if (this.data.atHardBreak) {
			let t = n.children[n.children.length - 1];
			t.position.end = Sl(e.end), this.data.atHardBreak = void 0;
			return;
		}
		!this.data.setextHeadingSlurpLineEnding && t.canContainEols.includes(n.type) && (T.call(this, e), E.call(this, e));
	}
	function O() {
		this.data.atHardBreak = !0;
	}
	function k() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.value = e;
	}
	function ee() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.value = e;
	}
	function A() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.value = e;
	}
	function j() {
		let e = this.stack[this.stack.length - 1];
		if (this.data.inReference) {
			let t = this.data.referenceType || "shortcut";
			e.type += "Reference", e.referenceType = t, delete e.url, delete e.title;
		} else delete e.identifier, delete e.label;
		this.data.referenceType = void 0;
	}
	function M() {
		let e = this.stack[this.stack.length - 1];
		if (this.data.inReference) {
			let t = this.data.referenceType || "shortcut";
			e.type += "Reference", e.referenceType = t, delete e.url, delete e.title;
		} else delete e.identifier, delete e.label;
		this.data.referenceType = void 0;
	}
	function N(e) {
		let t = this.sliceSerialize(e), n = this.stack[this.stack.length - 2];
		n.label = _l(t), n.identifier = Ho(t).toLowerCase();
	}
	function P() {
		let e = this.stack[this.stack.length - 1], t = this.resume(), n = this.stack[this.stack.length - 1];
		this.data.inReference = !0, n.type === "link" ? n.children = e.children : n.alt = t;
	}
	function te() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.url = e;
	}
	function ne() {
		let e = this.resume(), t = this.stack[this.stack.length - 1];
		t.title = e;
	}
	function re() {
		this.data.inReference = void 0;
	}
	function ie() {
		this.data.referenceType = "collapsed";
	}
	function F(e) {
		let t = this.resume(), n = this.stack[this.stack.length - 1];
		n.label = t, n.identifier = Ho(this.sliceSerialize(e)).toLowerCase(), this.data.referenceType = "full";
	}
	function ae(e) {
		this.data.characterReferenceType = e.type;
	}
	function oe(e) {
		let t = this.sliceSerialize(e), n = this.data.characterReferenceType, r;
		n ? (r = Vo(t, n === "characterReferenceMarkerNumeric" ? 10 : 16), this.data.characterReferenceType = void 0) : r = Po(t);
		let i = this.stack[this.stack.length - 1];
		i.value += r;
	}
	function se(e) {
		let t = this.stack.pop();
		t.position.end = Sl(e.end);
	}
	function ce(e) {
		E.call(this, e);
		let t = this.stack[this.stack.length - 1];
		t.url = this.sliceSerialize(e);
	}
	function le(e) {
		E.call(this, e);
		let t = this.stack[this.stack.length - 1];
		t.url = "mailto:" + this.sliceSerialize(e);
	}
	function ue() {
		return {
			type: "blockquote",
			children: []
		};
	}
	function de() {
		return {
			type: "code",
			lang: null,
			meta: null,
			value: ""
		};
	}
	function fe() {
		return {
			type: "inlineCode",
			value: ""
		};
	}
	function pe() {
		return {
			type: "definition",
			identifier: "",
			label: null,
			title: null,
			url: ""
		};
	}
	function me() {
		return {
			type: "emphasis",
			children: []
		};
	}
	function he() {
		return {
			type: "heading",
			depth: 0,
			children: []
		};
	}
	function I() {
		return { type: "break" };
	}
	function ge() {
		return {
			type: "html",
			value: ""
		};
	}
	function _e() {
		return {
			type: "image",
			title: null,
			url: "",
			alt: null
		};
	}
	function ve() {
		return {
			type: "link",
			title: null,
			url: "",
			children: []
		};
	}
	function ye(e) {
		return {
			type: "list",
			ordered: e.type === "listOrdered",
			start: null,
			spread: e._spread,
			children: []
		};
	}
	function be(e) {
		return {
			type: "listItem",
			spread: e._spread,
			checked: null,
			children: []
		};
	}
	function xe() {
		return {
			type: "paragraph",
			children: []
		};
	}
	function L() {
		return {
			type: "strong",
			children: []
		};
	}
	function Se() {
		return {
			type: "text",
			value: ""
		};
	}
	function Ce() {
		return { type: "thematicBreak" };
	}
}
function Sl(e) {
	return {
		line: e.line,
		column: e.column,
		offset: e.offset
	};
}
function Cl(e, t) {
	let n = -1;
	for (; ++n < t.length;) {
		let r = t[n];
		Array.isArray(r) ? Cl(e, r) : wl(e, r);
	}
}
function wl(e, t) {
	let n;
	for (n in t) if (yl.call(t, n)) switch (n) {
		case "canContainEols": {
			let r = t[n];
			r && e[n].push(...r);
			break;
		}
		case "transforms": {
			let r = t[n];
			r && e[n].push(...r);
			break;
		}
		case "enter":
		case "exit": {
			let r = t[n];
			r && Object.assign(e[n], r);
			break;
		}
	}
}
function Tl(e, t) {
	throw Error(e ? "Cannot close `" + e.type + "` (" + Ka({
		start: e.start,
		end: e.end
	}) + "): a different token (`" + t.type + "`, " + Ka({
		start: t.start,
		end: t.end
	}) + ") is open" : "Cannot close document, a token (`" + t.type + "`, " + Ka({
		start: t.start,
		end: t.end
	}) + ") is still open");
}
//#endregion
//#region node_modules/remark-parse/lib/index.js
function El(e) {
	let t = this;
	t.parser = n;
	function n(n) {
		return bl(n, {
			...t.data("settings"),
			...e,
			extensions: t.data("micromarkExtensions") || [],
			mdastExtensions: t.data("fromMarkdownExtensions") || []
		});
	}
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/blockquote.js
function Dl(e, t) {
	let n = {
		type: "element",
		tagName: "blockquote",
		properties: {},
		children: e.wrap(e.all(t), !0)
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/break.js
function Ol(e, t) {
	let n = {
		type: "element",
		tagName: "br",
		properties: {},
		children: []
	};
	return e.patch(t, n), [e.applyData(t, n), {
		type: "text",
		value: "\n"
	}];
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/code.js
function kl(e, t) {
	let n = t.value ? t.value + "\n" : "", r = {}, i = t.lang ? t.lang.split(/\s+/) : [];
	i.length > 0 && (r.className = ["language-" + i[0]]);
	let a = {
		type: "element",
		tagName: "code",
		properties: r,
		children: [{
			type: "text",
			value: n
		}]
	};
	return t.meta && (a.data = { meta: t.meta }), e.patch(t, a), a = e.applyData(t, a), a = {
		type: "element",
		tagName: "pre",
		properties: {},
		children: [a]
	}, e.patch(t, a), a;
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/delete.js
function Al(e, t) {
	let n = {
		type: "element",
		tagName: "del",
		properties: {},
		children: e.all(t)
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/emphasis.js
function jl(e, t) {
	let n = {
		type: "element",
		tagName: "em",
		properties: {},
		children: e.all(t)
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/footnote-reference.js
function Ml(e, t) {
	let n = typeof e.options.clobberPrefix == "string" ? e.options.clobberPrefix : "user-content-", r = String(t.identifier).toUpperCase(), i = es(r.toLowerCase()), a = e.footnoteOrder.indexOf(r), o, s = e.footnoteCounts.get(r);
	s === void 0 ? (s = 0, e.footnoteOrder.push(r), o = e.footnoteOrder.length) : o = a + 1, s += 1, e.footnoteCounts.set(r, s);
	let c = {
		type: "element",
		tagName: "a",
		properties: {
			href: "#" + n + "fn-" + i,
			id: n + "fnref-" + i + (s > 1 ? "-" + s : ""),
			dataFootnoteRef: !0,
			ariaDescribedBy: ["footnote-label"]
		},
		children: [{
			type: "text",
			value: String(o)
		}]
	};
	e.patch(t, c);
	let l = {
		type: "element",
		tagName: "sup",
		properties: {},
		children: [c]
	};
	return e.patch(t, l), e.applyData(t, l);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/heading.js
function Nl(e, t) {
	let n = {
		type: "element",
		tagName: "h" + t.depth,
		properties: {},
		children: e.all(t)
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/html.js
function Pl(e, t) {
	if (e.options.allowDangerousHtml) {
		let n = {
			type: "raw",
			value: t.value
		};
		return e.patch(t, n), e.applyData(t, n);
	}
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/revert.js
function Fl(e, t) {
	let n = t.referenceType, r = "]";
	if (n === "collapsed" ? r += "[]" : n === "full" && (r += "[" + (t.label || t.identifier) + "]"), t.type === "imageReference") return [{
		type: "text",
		value: "![" + t.alt + r
	}];
	let i = e.all(t), a = i[0];
	a && a.type === "text" ? a.value = "[" + a.value : i.unshift({
		type: "text",
		value: "["
	});
	let o = i[i.length - 1];
	return o && o.type === "text" ? o.value += r : i.push({
		type: "text",
		value: r
	}), i;
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/image-reference.js
function Il(e, t) {
	let n = String(t.identifier).toUpperCase(), r = e.definitionById.get(n);
	if (!r) return Fl(e, t);
	let i = {
		src: es(r.url || ""),
		alt: t.alt
	};
	r.title !== null && r.title !== void 0 && (i.title = r.title);
	let a = {
		type: "element",
		tagName: "img",
		properties: i,
		children: []
	};
	return e.patch(t, a), e.applyData(t, a);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/image.js
function Ll(e, t) {
	let n = { src: es(t.url) };
	t.alt !== null && t.alt !== void 0 && (n.alt = t.alt), t.title !== null && t.title !== void 0 && (n.title = t.title);
	let r = {
		type: "element",
		tagName: "img",
		properties: n,
		children: []
	};
	return e.patch(t, r), e.applyData(t, r);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/inline-code.js
function Rl(e, t) {
	let n = {
		type: "text",
		value: t.value.replace(/\r?\n|\r/g, " ")
	};
	e.patch(t, n);
	let r = {
		type: "element",
		tagName: "code",
		properties: {},
		children: [n]
	};
	return e.patch(t, r), e.applyData(t, r);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/link-reference.js
function zl(e, t) {
	let n = String(t.identifier).toUpperCase(), r = e.definitionById.get(n);
	if (!r) return Fl(e, t);
	let i = { href: es(r.url || "") };
	r.title !== null && r.title !== void 0 && (i.title = r.title);
	let a = {
		type: "element",
		tagName: "a",
		properties: i,
		children: e.all(t)
	};
	return e.patch(t, a), e.applyData(t, a);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/link.js
function Bl(e, t) {
	let n = { href: es(t.url) };
	t.title !== null && t.title !== void 0 && (n.title = t.title);
	let r = {
		type: "element",
		tagName: "a",
		properties: n,
		children: e.all(t)
	};
	return e.patch(t, r), e.applyData(t, r);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/list-item.js
function K(e, t, n) {
	let r = e.all(t), i = n ? q(n) : Vl(t), a = {}, o = [];
	if (typeof t.checked == "boolean") {
		let e = r[0], n;
		e && e.type === "element" && e.tagName === "p" ? n = e : (n = {
			type: "element",
			tagName: "p",
			properties: {},
			children: []
		}, r.unshift(n)), n.children.length > 0 && n.children.unshift({
			type: "text",
			value: " "
		}), n.children.unshift({
			type: "element",
			tagName: "input",
			properties: {
				type: "checkbox",
				checked: t.checked,
				disabled: !0
			},
			children: []
		}), a.className = ["task-list-item"];
	}
	let s = -1;
	for (; ++s < r.length;) {
		let e = r[s];
		(i || s !== 0 || e.type !== "element" || e.tagName !== "p") && o.push({
			type: "text",
			value: "\n"
		}), e.type === "element" && e.tagName === "p" && !i ? o.push(...e.children) : o.push(e);
	}
	let c = r[r.length - 1];
	c && (i || c.type !== "element" || c.tagName !== "p") && o.push({
		type: "text",
		value: "\n"
	});
	let l = {
		type: "element",
		tagName: "li",
		properties: a,
		children: o
	};
	return e.patch(t, l), e.applyData(t, l);
}
function q(e) {
	let t = !1;
	if (e.type === "list") {
		t = e.spread || !1;
		let n = e.children, r = -1;
		for (; !t && ++r < n.length;) t = Vl(n[r]);
	}
	return t;
}
function Vl(e) {
	return e.spread ?? e.children.length > 1;
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/list.js
function Hl(e, t) {
	let n = {}, r = e.all(t), i = -1;
	for (typeof t.start == "number" && t.start !== 1 && (n.start = t.start); ++i < r.length;) {
		let e = r[i];
		if (e.type === "element" && e.tagName === "li" && e.properties && Array.isArray(e.properties.className) && e.properties.className.includes("task-list-item")) {
			n.className = ["contains-task-list"];
			break;
		}
	}
	let a = {
		type: "element",
		tagName: t.ordered ? "ol" : "ul",
		properties: n,
		children: e.wrap(r, !0)
	};
	return e.patch(t, a), e.applyData(t, a);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/paragraph.js
function Ul(e, t) {
	let n = {
		type: "element",
		tagName: "p",
		properties: {},
		children: e.all(t)
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/root.js
function Wl(e, t) {
	let n = {
		type: "root",
		children: e.wrap(e.all(t))
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/strong.js
function Gl(e, t) {
	let n = {
		type: "element",
		tagName: "strong",
		properties: {},
		children: e.all(t)
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/table.js
function Kl(e, t) {
	let n = e.all(t), r = n.shift(), i = [];
	if (r) {
		let n = {
			type: "element",
			tagName: "thead",
			properties: {},
			children: e.wrap([r], !0)
		};
		e.patch(t.children[0], n), i.push(n);
	}
	if (n.length > 0) {
		let r = {
			type: "element",
			tagName: "tbody",
			properties: {},
			children: e.wrap(n, !0)
		}, a = Ua(t.children[1]), o = Ha(t.children[t.children.length - 1]);
		a && o && (r.position = {
			start: a,
			end: o
		}), i.push(r);
	}
	let a = {
		type: "element",
		tagName: "table",
		properties: {},
		children: e.wrap(i, !0)
	};
	return e.patch(t, a), e.applyData(t, a);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/table-row.js
function ql(e, t, n) {
	let r = n ? n.children : void 0, i = (r ? r.indexOf(t) : 1) === 0 ? "th" : "td", a = n && n.type === "table" ? n.align : void 0, o = a ? a.length : t.children.length, s = -1, c = [];
	for (; ++s < o;) {
		let n = t.children[s], r = {}, o = a ? a[s] : void 0;
		o && (r.align = o);
		let l = {
			type: "element",
			tagName: i,
			properties: r,
			children: []
		};
		n && (l.children = e.all(n), e.patch(n, l), l = e.applyData(n, l)), c.push(l);
	}
	let l = {
		type: "element",
		tagName: "tr",
		properties: {},
		children: e.wrap(c, !0)
	};
	return e.patch(t, l), e.applyData(t, l);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/table-cell.js
function Jl(e, t) {
	let n = {
		type: "element",
		tagName: "td",
		properties: {},
		children: e.all(t)
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/trim-lines/index.js
var Yl = 9, Xl = 32;
function Zl(e) {
	let t = String(e), n = /\r?\n|\r/g, r = n.exec(t), i = 0, a = [];
	for (; r;) a.push(Ql(t.slice(i, r.index), i > 0, !0), r[0]), i = r.index + r[0].length, r = n.exec(t);
	return a.push(Ql(t.slice(i), i > 0, !1)), a.join("");
}
function Ql(e, t, n) {
	let r = 0, i = e.length;
	if (t) {
		let t = e.codePointAt(r);
		for (; t === Yl || t === Xl;) r++, t = e.codePointAt(r);
	}
	if (n) {
		let t = e.codePointAt(i - 1);
		for (; t === Yl || t === Xl;) i--, t = e.codePointAt(i - 1);
	}
	return i > r ? e.slice(r, i) : "";
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/text.js
function $l(e, t) {
	let n = {
		type: "text",
		value: Zl(String(t.value))
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/thematic-break.js
function eu(e, t) {
	let n = {
		type: "element",
		tagName: "hr",
		properties: {},
		children: []
	};
	return e.patch(t, n), e.applyData(t, n);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/handlers/index.js
var tu = {
	blockquote: Dl,
	break: Ol,
	code: kl,
	delete: Al,
	emphasis: jl,
	footnoteReference: Ml,
	heading: Nl,
	html: Pl,
	imageReference: Il,
	image: Ll,
	inlineCode: Rl,
	linkReference: zl,
	link: Bl,
	listItem: K,
	list: Hl,
	paragraph: Ul,
	root: Wl,
	strong: Gl,
	table: Kl,
	tableCell: Jl,
	tableRow: ql,
	text: $l,
	thematicBreak: eu,
	toml: nu,
	yaml: nu,
	definition: nu,
	footnoteDefinition: nu
};
function nu() {}
//#endregion
//#region node_modules/@ungap/structured-clone/esm/deserialize.js
var ru = typeof self == "object" ? self : globalThis, iu = (e, t) => {
	switch (e) {
		case "Function":
		case "SharedWorker":
		case "Worker":
		case "eval":
		case "setInterval":
		case "setTimeout": throw TypeError("unable to deserialize " + e);
	}
	return new ru[e](t);
}, au = (e, t) => {
	let n = (t, n) => (e.set(n, t), t), r = (i) => {
		if (e.has(i)) return e.get(i);
		let [a, o] = t[i];
		switch (a) {
			case 0:
			case -1: return n(o, i);
			case 1: {
				let e = n([], i);
				for (let t of o) e.push(r(t));
				return e;
			}
			case 2: {
				let e = n({}, i);
				for (let [t, n] of o) e[r(t)] = r(n);
				return e;
			}
			case 3: return n(new Date(o), i);
			case 4: {
				let { source: e, flags: t } = o;
				return n(new RegExp(e, t), i);
			}
			case 5: {
				let e = n(/* @__PURE__ */ new Map(), i);
				for (let [t, n] of o) e.set(r(t), r(n));
				return e;
			}
			case 6: {
				let e = n(/* @__PURE__ */ new Set(), i);
				for (let t of o) e.add(r(t));
				return e;
			}
			case 7: {
				let { name: e, message: t } = o;
				return n(typeof ru[e] == "function" ? iu(e, t) : Error(t), i);
			}
			case 8: return n(BigInt(o), i);
			case "BigInt": return n(Object(BigInt(o)), i);
			case "ArrayBuffer": return n(new Uint8Array(o).buffer, o);
			case "DataView": {
				let { buffer: e } = new Uint8Array(o);
				return n(new DataView(e), o);
			}
		}
		return n(iu(a, o), i);
	};
	return r;
}, ou = (e) => au(/* @__PURE__ */ new Map(), e)(0), su = "", { toString: cu } = {}, { keys: lu } = Object, uu = (e) => {
	let t = typeof e;
	if (t !== "object" || !e) return [0, t];
	let n = cu.call(e).slice(8, -1);
	switch (n) {
		case "Array": return [1, su];
		case "Object": return [2, su];
		case "Date": return [3, su];
		case "RegExp": return [4, su];
		case "Map": return [5, su];
		case "Set": return [6, su];
		case "DataView": return [1, n];
	}
	return n.includes("Array") ? [1, n] : e instanceof Error ? [7, e.name || "Error"] : [2, n];
}, du = ([e, t]) => e === 0 && (t === "function" || t === "symbol"), fu = (e, t, n, r) => {
	let i = (e, t) => {
		let i = r.push(e) - 1;
		return n.set(t, i), i;
	}, a = (r) => {
		if (n.has(r)) return n.get(r);
		let [o, s] = uu(r);
		switch (o) {
			case 0: {
				let t = r;
				switch (s) {
					case "bigint":
						o = 8, t = r.toString();
						break;
					case "function":
					case "symbol":
						if (e) throw TypeError("unable to serialize " + s);
						t = null;
						break;
					case "undefined": return i([-1], r);
				}
				return i([o, t], r);
			}
			case 1: {
				if (s) {
					let e = r;
					return s === "DataView" ? e = new Uint8Array(r.buffer) : s === "ArrayBuffer" && (e = new Uint8Array(r)), i([s, [...e]], r);
				}
				let e = [], t = i([o, e], r);
				for (let t of r) e.push(a(t));
				return t;
			}
			case 2: {
				if (s) switch (s) {
					case "BigInt": return i([s, r.toString()], r);
					case "Boolean":
					case "Number":
					case "String": return i([s, r.valueOf()], r);
				}
				if (t && "toJSON" in r) return a(r.toJSON());
				let n = [], c = i([o, n], r);
				for (let t of lu(r)) (e || !du(uu(r[t]))) && n.push([a(t), a(r[t])]);
				return c;
			}
			case 3: return i([o, isNaN(r.getTime()) ? su : r.toISOString()], r);
			case 4: {
				let { source: e, flags: t } = r;
				return i([o, {
					source: e,
					flags: t
				}], r);
			}
			case 5: {
				let t = [], n = i([o, t], r);
				for (let [n, i] of r) (e || !(du(uu(n)) || du(uu(i)))) && t.push([a(n), a(i)]);
				return n;
			}
			case 6: {
				let t = [], n = i([o, t], r);
				for (let n of r) (e || !du(uu(n))) && t.push(a(n));
				return n;
			}
		}
		let { message: c } = r;
		return i([o, {
			name: s,
			message: c
		}], r);
	};
	return a;
}, pu = (e, { json: t, lossy: n } = {}) => {
	let r = [];
	return fu(!(t || n), !!t, /* @__PURE__ */ new Map(), r)(e), r;
}, mu = typeof structuredClone == "function" ? (e, t) => t && ("json" in t || "lossy" in t) ? ou(pu(e, t)) : structuredClone(e) : (e, t) => ou(pu(e, t));
//#endregion
//#region node_modules/mdast-util-to-hast/lib/footer.js
function hu(e, t) {
	let n = [{
		type: "text",
		value: "↩"
	}];
	return t > 1 && n.push({
		type: "element",
		tagName: "sup",
		properties: {},
		children: [{
			type: "text",
			value: String(t)
		}]
	}), n;
}
function gu(e, t) {
	return "Back to reference " + (e + 1) + (t > 1 ? "-" + t : "");
}
function _u(e) {
	let t = typeof e.options.clobberPrefix == "string" ? e.options.clobberPrefix : "user-content-", n = e.options.footnoteBackContent || hu, r = e.options.footnoteBackLabel || gu, i = e.options.footnoteLabel || "Footnotes", a = e.options.footnoteLabelTagName || "h2", o = e.options.footnoteLabelProperties || { className: ["sr-only"] }, s = [], c = -1;
	for (; ++c < e.footnoteOrder.length;) {
		let i = e.footnoteById.get(e.footnoteOrder[c]);
		if (!i) continue;
		let a = e.all(i), o = String(i.identifier).toUpperCase(), l = es(o.toLowerCase()), u = 0, d = [], f = e.footnoteCounts.get(o);
		for (; f !== void 0 && ++u <= f;) {
			d.length > 0 && d.push({
				type: "text",
				value: " "
			});
			let e = typeof n == "string" ? n : n(c, u);
			typeof e == "string" && (e = {
				type: "text",
				value: e
			}), d.push({
				type: "element",
				tagName: "a",
				properties: {
					href: "#" + t + "fnref-" + l + (u > 1 ? "-" + u : ""),
					dataFootnoteBackref: "",
					ariaLabel: typeof r == "string" ? r : r(c, u),
					className: ["data-footnote-backref"]
				},
				children: Array.isArray(e) ? e : [e]
			});
		}
		let p = a[a.length - 1];
		if (p && p.type === "element" && p.tagName === "p") {
			let e = p.children[p.children.length - 1];
			e && e.type === "text" ? e.value += " " : p.children.push({
				type: "text",
				value: " "
			}), p.children.push(...d);
		} else a.push(...d);
		let m = {
			type: "element",
			tagName: "li",
			properties: { id: t + "fn-" + l },
			children: e.wrap(a, !0)
		};
		e.patch(i, m), s.push(m);
	}
	if (s.length !== 0) return {
		type: "element",
		tagName: "section",
		properties: {
			dataFootnotes: !0,
			className: ["footnotes"]
		},
		children: [
			{
				type: "element",
				tagName: a,
				properties: {
					...mu(o),
					id: "footnote-label"
				},
				children: [{
					type: "text",
					value: i
				}]
			},
			{
				type: "text",
				value: "\n"
			},
			{
				type: "element",
				tagName: "ol",
				properties: {},
				children: e.wrap(s, !0)
			},
			{
				type: "text",
				value: "\n"
			}
		]
	};
}
//#endregion
//#region node_modules/unist-util-is/lib/index.js
var vu = (function(e) {
	if (e == null) return Cu;
	if (typeof e == "function") return Su(e);
	if (typeof e == "object") return Array.isArray(e) ? yu(e) : bu(e);
	if (typeof e == "string") return xu(e);
	throw Error("Expected function, string, or object as test");
});
function yu(e) {
	let t = [], n = -1;
	for (; ++n < e.length;) t[n] = vu(e[n]);
	return Su(r);
	function r(...e) {
		let n = -1;
		for (; ++n < t.length;) if (t[n].apply(this, e)) return !0;
		return !1;
	}
}
function bu(e) {
	let t = e;
	return Su(n);
	function n(n) {
		let r = n, i;
		for (i in e) if (r[i] !== t[i]) return !1;
		return !0;
	}
}
function xu(e) {
	return Su(t);
	function t(t) {
		return t && t.type === e;
	}
}
function Su(e) {
	return t;
	function t(t, n, r) {
		return !!(wu(t) && e.call(this, t, typeof n == "number" ? n : void 0, r || void 0));
	}
}
function Cu() {
	return !0;
}
function wu(e) {
	return typeof e == "object" && !!e && "type" in e;
}
//#endregion
//#region node_modules/unist-util-visit-parents/lib/color.js
function Tu(e) {
	return e;
}
//#endregion
//#region node_modules/unist-util-visit-parents/lib/index.js
var Eu = [];
function Du(e, t, n, r) {
	let i;
	typeof t == "function" && typeof n != "function" ? (r = n, n = t) : i = t;
	let a = vu(i), o = r ? -1 : 1;
	s(e, void 0, [])();
	function s(e, i, c) {
		let l = e && typeof e == "object" ? e : {};
		if (typeof l.type == "string") {
			let t = typeof l.tagName == "string" ? l.tagName : typeof l.name == "string" ? l.name : void 0;
			Object.defineProperty(u, "name", { value: "node (" + Tu(e.type + (t ? "<" + t + ">" : "")) + ")" });
		}
		return u;
		function u() {
			let l = Eu, u, d, f;
			if ((!t || a(e, i, c[c.length - 1] || void 0)) && (l = Ou(n(e, c)), l[0] === !1)) return l;
			if ("children" in e && e.children) {
				let t = e;
				if (t.children && l[0] !== "skip") for (d = (r ? t.children.length : -1) + o, f = c.concat(t); d > -1 && d < t.children.length;) {
					let e = t.children[d];
					if (u = s(e, d, f)(), u[0] === !1) return u;
					d = typeof u[1] == "number" ? u[1] : d + o;
				}
			}
			return l;
		}
	}
}
function Ou(e) {
	return Array.isArray(e) ? e : typeof e == "number" ? [!0, e] : e == null ? Eu : [e];
}
//#endregion
//#region node_modules/unist-util-visit/lib/index.js
function ku(e, t, n, r) {
	let i, a, o;
	typeof t == "function" && typeof n != "function" ? (a = void 0, o = t, i = n) : (a = t, o = n, i = r), Du(e, a, s, i);
	function s(e, t) {
		let n = t[t.length - 1], r = n ? n.children.indexOf(e) : void 0;
		return o(e, r, n);
	}
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/state.js
var Au = {}.hasOwnProperty, ju = {};
function Mu(e, t) {
	let n = t || ju, r = /* @__PURE__ */ new Map(), i = /* @__PURE__ */ new Map(), a = {
		all: s,
		applyData: Pu,
		definitionById: r,
		footnoteById: i,
		footnoteCounts: /* @__PURE__ */ new Map(),
		footnoteOrder: [],
		handlers: {
			...tu,
			...n.handlers
		},
		one: o,
		options: n,
		patch: Nu,
		wrap: Iu
	};
	return ku(e, function(e) {
		if (e.type === "definition" || e.type === "footnoteDefinition") {
			let t = e.type === "definition" ? r : i, n = String(e.identifier).toUpperCase();
			t.has(n) || t.set(n, e);
		}
	}), a;
	function o(e, t) {
		let n = e.type, r = a.handlers[n];
		if (Au.call(a.handlers, n) && r) return r(a, e, t);
		if (a.options.passThrough && a.options.passThrough.includes(n)) {
			if ("children" in e) {
				let { children: t, ...n } = e, r = mu(n);
				return r.children = a.all(e), r;
			}
			return mu(e);
		}
		return (a.options.unknownHandler || Fu)(a, e, t);
	}
	function s(e) {
		let t = [];
		if ("children" in e) {
			let n = e.children, r = -1;
			for (; ++r < n.length;) {
				let i = a.one(n[r], e);
				if (i) {
					if (r && n[r - 1].type === "break" && (!Array.isArray(i) && i.type === "text" && (i.value = Lu(i.value)), !Array.isArray(i) && i.type === "element")) {
						let e = i.children[0];
						e && e.type === "text" && (e.value = Lu(e.value));
					}
					Array.isArray(i) ? t.push(...i) : t.push(i);
				}
			}
		}
		return t;
	}
}
function Nu(e, t) {
	e.position && (t.position = Ga(e));
}
function Pu(e, t) {
	let n = t;
	if (e && e.data) {
		let t = e.data.hName, r = e.data.hChildren, i = e.data.hProperties;
		typeof t == "string" && (n.type === "element" ? n.tagName = t : n = {
			type: "element",
			tagName: t,
			properties: {},
			children: "children" in n ? n.children : [n]
		}), n.type === "element" && i && Object.assign(n.properties, mu(i)), "children" in n && n.children && r != null && (n.children = r);
	}
	return n;
}
function Fu(e, t) {
	let n = t.data || {}, r = "value" in t && !(Au.call(n, "hProperties") || Au.call(n, "hChildren")) ? {
		type: "text",
		value: t.value
	} : {
		type: "element",
		tagName: "div",
		properties: {},
		children: e.all(t)
	};
	return e.patch(t, r), e.applyData(t, r);
}
function Iu(e, t) {
	let n = [], r = -1;
	for (t && n.push({
		type: "text",
		value: "\n"
	}); ++r < e.length;) r && n.push({
		type: "text",
		value: "\n"
	}), n.push(e[r]);
	return t && e.length > 0 && n.push({
		type: "text",
		value: "\n"
	}), n;
}
function Lu(e) {
	let t = 0, n = e.charCodeAt(t);
	for (; n === 9 || n === 32;) t++, n = e.charCodeAt(t);
	return e.slice(t);
}
//#endregion
//#region node_modules/mdast-util-to-hast/lib/index.js
function Ru(e, t) {
	let n = Mu(e, t), r = n.one(e, void 0), i = _u(n), a = Array.isArray(r) ? {
		type: "root",
		children: r
	} : r || {
		type: "root",
		children: []
	};
	return i && ("children" in a, a.children.push({
		type: "text",
		value: "\n"
	}, i)), a;
}
//#endregion
//#region node_modules/remark-rehype/lib/index.js
function zu(e, t) {
	return e && "run" in e ? async function(n, r) {
		let i = Ru(n, {
			file: r,
			...t
		});
		await e.run(i, r);
	} : function(n, r) {
		return Ru(n, {
			file: r,
			...e || t
		});
	};
}
//#endregion
//#region node_modules/bail/index.js
function Bu(e) {
	if (e) throw e;
}
//#endregion
//#region node_modules/extend/index.js
var Vu = /* @__PURE__ */ n(((e, t) => {
	var n = Object.prototype.hasOwnProperty, r = Object.prototype.toString, i = Object.defineProperty, a = Object.getOwnPropertyDescriptor, o = function(e) {
		return typeof Array.isArray == "function" ? Array.isArray(e) : r.call(e) === "[object Array]";
	}, s = function(e) {
		if (!e || r.call(e) !== "[object Object]") return !1;
		var t = n.call(e, "constructor"), i = e.constructor && e.constructor.prototype && n.call(e.constructor.prototype, "isPrototypeOf");
		if (e.constructor && !t && !i) return !1;
		for (var a in e);
		return a === void 0 || n.call(e, a);
	}, c = function(e, t) {
		i && t.name === "__proto__" ? i(e, t.name, {
			enumerable: !0,
			configurable: !0,
			value: t.newValue,
			writable: !0
		}) : e[t.name] = t.newValue;
	}, l = function(e, t) {
		if (t === "__proto__") {
			if (!n.call(e, t)) return;
			if (a) return a(e, t).value;
		}
		return e[t];
	};
	t.exports = function e() {
		var t, n, r, i, a, u, d = arguments[0], f = 1, p = arguments.length, m = !1;
		for (typeof d == "boolean" && (m = d, d = arguments[1] || {}, f = 2), (d == null || typeof d != "object" && typeof d != "function") && (d = {}); f < p; ++f) if (t = arguments[f], t != null) for (n in t) r = l(d, n), i = l(t, n), d !== i && (m && i && (s(i) || (a = o(i))) ? (a ? (a = !1, u = r && o(r) ? r : []) : u = r && s(r) ? r : {}, c(d, {
			name: n,
			newValue: e(m, u, i)
		})) : i !== void 0 && c(d, {
			name: n,
			newValue: i
		}));
		return d;
	};
}));
//#endregion
//#region node_modules/is-plain-obj/index.js
function Hu(e) {
	if (typeof e != "object" || !e) return !1;
	let t = Object.getPrototypeOf(e);
	return (t === null || t === Object.prototype || Object.getPrototypeOf(t) === null) && !(Symbol.toStringTag in e) && !(Symbol.iterator in e);
}
//#endregion
//#region node_modules/trough/lib/index.js
function Uu() {
	let e = [], t = {
		run: n,
		use: r
	};
	return t;
	function n(...t) {
		let n = -1, r = t.pop();
		if (typeof r != "function") throw TypeError("Expected function as last argument, not " + r);
		i(null, ...t);
		function i(a, ...o) {
			let s = e[++n], c = -1;
			if (a) {
				r(a);
				return;
			}
			for (; ++c < t.length;) (o[c] === null || o[c] === void 0) && (o[c] = t[c]);
			t = o, s ? Wu(s, i)(...o) : r(null, ...o);
		}
	}
	function r(n) {
		if (typeof n != "function") throw TypeError("Expected `middelware` to be a function, not " + n);
		return e.push(n), t;
	}
}
function Wu(e, t) {
	let n;
	return r;
	function r(...t) {
		let r = e.length > t.length, o;
		r && t.push(i);
		try {
			o = e.apply(this, t);
		} catch (e) {
			let t = e;
			if (r && n) throw t;
			return i(t);
		}
		r || (o && o.then && typeof o.then == "function" ? o.then(a, i) : o instanceof Error ? i(o) : a(o));
	}
	function i(e, ...r) {
		n || (n = !0, t(e, ...r));
	}
	function a(e) {
		i(null, e);
	}
}
//#endregion
//#region node_modules/vfile/lib/minpath.browser.js
var Gu = {
	basename: Ku,
	dirname: qu,
	extname: Ju,
	join: Yu,
	sep: "/"
};
function Ku(e, t) {
	if (t !== void 0 && typeof t != "string") throw TypeError("\"ext\" argument must be a string");
	Qu(e);
	let n = 0, r = -1, i = e.length, a;
	if (t === void 0 || t.length === 0 || t.length > e.length) {
		for (; i--;) if (e.codePointAt(i) === 47) {
			if (a) {
				n = i + 1;
				break;
			}
		} else r < 0 && (a = !0, r = i + 1);
		return r < 0 ? "" : e.slice(n, r);
	}
	if (t === e) return "";
	let o = -1, s = t.length - 1;
	for (; i--;) if (e.codePointAt(i) === 47) {
		if (a) {
			n = i + 1;
			break;
		}
	} else o < 0 && (a = !0, o = i + 1), s > -1 && (e.codePointAt(i) === t.codePointAt(s--) ? s < 0 && (r = i) : (s = -1, r = o));
	return n === r ? r = o : r < 0 && (r = e.length), e.slice(n, r);
}
function qu(e) {
	if (Qu(e), e.length === 0) return ".";
	let t = -1, n = e.length, r;
	for (; --n;) if (e.codePointAt(n) === 47) {
		if (r) {
			t = n;
			break;
		}
	} else r ||= !0;
	return t < 0 ? e.codePointAt(0) === 47 ? "/" : "." : t === 1 && e.codePointAt(0) === 47 ? "//" : e.slice(0, t);
}
function Ju(e) {
	Qu(e);
	let t = e.length, n = -1, r = 0, i = -1, a = 0, o;
	for (; t--;) {
		let s = e.codePointAt(t);
		if (s === 47) {
			if (o) {
				r = t + 1;
				break;
			}
			continue;
		}
		n < 0 && (o = !0, n = t + 1), s === 46 ? i < 0 ? i = t : a !== 1 && (a = 1) : i > -1 && (a = -1);
	}
	return i < 0 || n < 0 || a === 0 || a === 1 && i === n - 1 && i === r + 1 ? "" : e.slice(i, n);
}
function Yu(...e) {
	let t = -1, n;
	for (; ++t < e.length;) Qu(e[t]), e[t] && (n = n === void 0 ? e[t] : n + "/" + e[t]);
	return n === void 0 ? "." : Xu(n);
}
function Xu(e) {
	Qu(e);
	let t = e.codePointAt(0) === 47, n = Zu(e, !t);
	return n.length === 0 && !t && (n = "."), n.length > 0 && e.codePointAt(e.length - 1) === 47 && (n += "/"), t ? "/" + n : n;
}
function Zu(e, t) {
	let n = "", r = 0, i = -1, a = 0, o = -1, s, c;
	for (; ++o <= e.length;) {
		if (o < e.length) s = e.codePointAt(o);
		else if (s === 47) break;
		else s = 47;
		if (s === 47) {
			if (!(i === o - 1 || a === 1)) if (i !== o - 1 && a === 2) {
				if (n.length < 2 || r !== 2 || n.codePointAt(n.length - 1) !== 46 || n.codePointAt(n.length - 2) !== 46) {
					if (n.length > 2) {
						if (c = n.lastIndexOf("/"), c !== n.length - 1) {
							c < 0 ? (n = "", r = 0) : (n = n.slice(0, c), r = n.length - 1 - n.lastIndexOf("/")), i = o, a = 0;
							continue;
						}
					} else if (n.length > 0) {
						n = "", r = 0, i = o, a = 0;
						continue;
					}
				}
				t && (n = n.length > 0 ? n + "/.." : "..", r = 2);
			} else n.length > 0 ? n += "/" + e.slice(i + 1, o) : n = e.slice(i + 1, o), r = o - i - 1;
			i = o, a = 0;
		} else s === 46 && a > -1 ? a++ : a = -1;
	}
	return n;
}
function Qu(e) {
	if (typeof e != "string") throw TypeError("Path must be a string. Received " + JSON.stringify(e));
}
//#endregion
//#region node_modules/vfile/lib/minproc.browser.js
var $u = { cwd: ed };
function ed() {
	return "/";
}
//#endregion
//#region node_modules/vfile/lib/minurl.shared.js
function td(e) {
	return !!(typeof e == "object" && e && "href" in e && e.href && "protocol" in e && e.protocol && e.auth === void 0);
}
//#endregion
//#region node_modules/vfile/lib/minurl.browser.js
function nd(e) {
	if (typeof e == "string") e = new URL(e);
	else if (!td(e)) {
		let t = /* @__PURE__ */ TypeError("The \"path\" argument must be of type string or an instance of URL. Received `" + e + "`");
		throw t.code = "ERR_INVALID_ARG_TYPE", t;
	}
	if (e.protocol !== "file:") {
		let e = /* @__PURE__ */ TypeError("The URL must be of scheme file");
		throw e.code = "ERR_INVALID_URL_SCHEME", e;
	}
	return rd(e);
}
function rd(e) {
	if (e.hostname !== "") {
		let e = /* @__PURE__ */ TypeError("File URL host must be \"localhost\" or empty on darwin");
		throw e.code = "ERR_INVALID_FILE_URL_HOST", e;
	}
	let t = e.pathname, n = -1;
	for (; ++n < t.length;) if (t.codePointAt(n) === 37 && t.codePointAt(n + 1) === 50) {
		let e = t.codePointAt(n + 2);
		if (e === 70 || e === 102) {
			let e = /* @__PURE__ */ TypeError("File URL path must not include encoded / characters");
			throw e.code = "ERR_INVALID_FILE_URL_PATH", e;
		}
	}
	return decodeURIComponent(t);
}
//#endregion
//#region node_modules/vfile/lib/index.js
var id = [
	"history",
	"path",
	"basename",
	"stem",
	"extname",
	"dirname"
], ad = class {
	constructor(e) {
		let t;
		t = e ? td(e) ? { path: e } : typeof e == "string" || ld(e) ? { value: e } : e : {}, this.cwd = "cwd" in t ? "" : $u.cwd(), this.data = {}, this.history = [], this.messages = [], this.value, this.map, this.result, this.stored;
		let n = -1;
		for (; ++n < id.length;) {
			let e = id[n];
			e in t && t[e] !== void 0 && t[e] !== null && (this[e] = e === "history" ? [...t[e]] : t[e]);
		}
		let r;
		for (r in t) id.includes(r) || (this[r] = t[r]);
	}
	get basename() {
		return typeof this.path == "string" ? Gu.basename(this.path) : void 0;
	}
	set basename(e) {
		sd(e, "basename"), od(e, "basename"), this.path = Gu.join(this.dirname || "", e);
	}
	get dirname() {
		return typeof this.path == "string" ? Gu.dirname(this.path) : void 0;
	}
	set dirname(e) {
		cd(this.basename, "dirname"), this.path = Gu.join(e || "", this.basename);
	}
	get extname() {
		return typeof this.path == "string" ? Gu.extname(this.path) : void 0;
	}
	set extname(e) {
		if (od(e, "extname"), cd(this.dirname, "extname"), e) {
			if (e.codePointAt(0) !== 46) throw Error("`extname` must start with `.`");
			if (e.includes(".", 1)) throw Error("`extname` cannot contain multiple dots");
		}
		this.path = Gu.join(this.dirname, this.stem + (e || ""));
	}
	get path() {
		return this.history[this.history.length - 1];
	}
	set path(e) {
		td(e) && (e = nd(e)), sd(e, "path"), this.path !== e && this.history.push(e);
	}
	get stem() {
		return typeof this.path == "string" ? Gu.basename(this.path, this.extname) : void 0;
	}
	set stem(e) {
		sd(e, "stem"), od(e, "stem"), this.path = Gu.join(this.dirname || "", e + (this.extname || ""));
	}
	fail(e, t, n) {
		let r = this.message(e, t, n);
		throw r.fatal = !0, r;
	}
	info(e, t, n) {
		let r = this.message(e, t, n);
		return r.fatal = void 0, r;
	}
	message(e, t, n) {
		let r = new Xa(e, t, n);
		return this.path && (r.name = this.path + ":" + r.name, r.file = this.path), r.fatal = !1, this.messages.push(r), r;
	}
	toString(e) {
		return this.value === void 0 ? "" : typeof this.value == "string" ? this.value : new TextDecoder(e || void 0).decode(this.value);
	}
};
function od(e, t) {
	if (e && e.includes(Gu.sep)) throw Error("`" + t + "` cannot be a path: did not expect `" + Gu.sep + "`");
}
function sd(e, t) {
	if (!e) throw Error("`" + t + "` cannot be empty");
}
function cd(e, t) {
	if (!e) throw Error("Setting `" + t + "` requires `path` to be set too");
}
function ld(e) {
	return !!(e && typeof e == "object" && "byteLength" in e && "byteOffset" in e);
}
//#endregion
//#region node_modules/unified/lib/callable-instance.js
var ud = (function(e) {
	let t = this.constructor.prototype, n = t[e], r = function() {
		return n.apply(r, arguments);
	};
	return Object.setPrototypeOf(r, t), r;
}), dd = /* @__PURE__ */ e(Vu(), 1), fd = {}.hasOwnProperty, pd = new class e extends ud {
	constructor() {
		super("copy"), this.Compiler = void 0, this.Parser = void 0, this.attachers = [], this.compiler = void 0, this.freezeIndex = -1, this.frozen = void 0, this.namespace = {}, this.parser = void 0, this.transformers = Uu();
	}
	copy() {
		let t = new e(), n = -1;
		for (; ++n < this.attachers.length;) {
			let e = this.attachers[n];
			t.use(...e);
		}
		return t.data((0, dd.default)(!0, {}, this.namespace)), t;
	}
	data(e, t) {
		return typeof e == "string" ? arguments.length === 2 ? (gd("data", this.frozen), this.namespace[e] = t, this) : fd.call(this.namespace, e) && this.namespace[e] || void 0 : e ? (gd("data", this.frozen), this.namespace = e, this) : this.namespace;
	}
	freeze() {
		if (this.frozen) return this;
		let e = this;
		for (; ++this.freezeIndex < this.attachers.length;) {
			let [t, ...n] = this.attachers[this.freezeIndex];
			if (n[0] === !1) continue;
			n[0] === !0 && (n[0] = void 0);
			let r = t.call(e, ...n);
			typeof r == "function" && this.transformers.use(r);
		}
		return this.frozen = !0, this.freezeIndex = Infinity, this;
	}
	parse(e) {
		this.freeze();
		let t = yd(e), n = this.parser || this.Parser;
		return md("parse", n), n(String(t), t);
	}
	process(e, t) {
		let n = this;
		return this.freeze(), md("process", this.parser || this.Parser), hd("process", this.compiler || this.Compiler), t ? r(void 0, t) : new Promise(r);
		function r(r, i) {
			let a = yd(e), o = n.parse(a);
			n.run(o, a, function(e, t, r) {
				if (e || !t || !r) return s(e);
				let i = t, a = n.stringify(i, r);
				xd(a) ? r.value = a : r.result = a, s(e, r);
			});
			function s(e, n) {
				e || !n ? i(e) : r ? r(n) : t(void 0, n);
			}
		}
	}
	processSync(e) {
		let t = !1, n;
		return this.freeze(), md("processSync", this.parser || this.Parser), hd("processSync", this.compiler || this.Compiler), this.process(e, r), vd("processSync", "process", t), n;
		function r(e, r) {
			t = !0, Bu(e), n = r;
		}
	}
	run(e, t, n) {
		_d(e), this.freeze();
		let r = this.transformers;
		return !n && typeof t == "function" && (n = t, t = void 0), n ? i(void 0, n) : new Promise(i);
		function i(i, a) {
			let o = yd(t);
			r.run(e, o, s);
			function s(t, r, o) {
				let s = r || e;
				t ? a(t) : i ? i(s) : n(void 0, s, o);
			}
		}
	}
	runSync(e, t) {
		let n = !1, r;
		return this.run(e, t, i), vd("runSync", "run", n), r;
		function i(e, t) {
			Bu(e), r = t, n = !0;
		}
	}
	stringify(e, t) {
		this.freeze();
		let n = yd(t), r = this.compiler || this.Compiler;
		return hd("stringify", r), _d(e), r(e, n);
	}
	use(e, ...t) {
		let n = this.attachers, r = this.namespace;
		if (gd("use", this.frozen), e != null) if (typeof e == "function") s(e, t);
		else if (typeof e == "object") Array.isArray(e) ? o(e) : a(e);
		else throw TypeError("Expected usable value, not `" + e + "`");
		return this;
		function i(e) {
			if (typeof e == "function") s(e, []);
			else if (typeof e == "object") if (Array.isArray(e)) {
				let [t, ...n] = e;
				s(t, n);
			} else a(e);
			else throw TypeError("Expected usable value, not `" + e + "`");
		}
		function a(e) {
			if (!("plugins" in e) && !("settings" in e)) throw Error("Expected usable value but received an empty preset, which is probably a mistake: presets typically come with `plugins` and sometimes with `settings`, but this has neither");
			o(e.plugins), e.settings && (r.settings = (0, dd.default)(!0, r.settings, e.settings));
		}
		function o(e) {
			let t = -1;
			if (e != null) if (Array.isArray(e)) for (; ++t < e.length;) {
				let n = e[t];
				i(n);
			}
			else throw TypeError("Expected a list of plugins, not `" + e + "`");
		}
		function s(e, t) {
			let r = -1, i = -1;
			for (; ++r < n.length;) if (n[r][0] === e) {
				i = r;
				break;
			}
			if (i === -1) n.push([e, ...t]);
			else if (t.length > 0) {
				let [r, ...a] = t, o = n[i][1];
				Hu(o) && Hu(r) && (r = (0, dd.default)(!0, o, r)), n[i] = [
					e,
					r,
					...a
				];
			}
		}
	}
}().freeze();
function md(e, t) {
	if (typeof t != "function") throw TypeError("Cannot `" + e + "` without `parser`");
}
function hd(e, t) {
	if (typeof t != "function") throw TypeError("Cannot `" + e + "` without `compiler`");
}
function gd(e, t) {
	if (t) throw Error("Cannot call `" + e + "` on a frozen processor.\nCreate a new processor first, by calling it: use `processor()` instead of `processor`.");
}
function _d(e) {
	if (!Hu(e) || typeof e.type != "string") throw TypeError("Expected node, got `" + e + "`");
}
function vd(e, t, n) {
	if (!n) throw Error("`" + e + "` finished async. Use `" + t + "` instead");
}
function yd(e) {
	return bd(e) ? e : new ad(e);
}
function bd(e) {
	return !!(e && typeof e == "object" && "message" in e && "messages" in e);
}
function xd(e) {
	return typeof e == "string" || Sd(e);
}
function Sd(e) {
	return !!(e && typeof e == "object" && "byteLength" in e && "byteOffset" in e);
}
//#endregion
//#region node_modules/react-markdown/lib/index.js
var J = Do(), Y = [], Cd = { allowDangerousHtml: !0 }, wd = /^(https?|ircs?|mailto|xmpp)$/i, Td = [
	{
		from: "astPlugins",
		id: "remove-buggy-html-in-markdown-parser"
	},
	{
		from: "allowDangerousHtml",
		id: "remove-buggy-html-in-markdown-parser"
	},
	{
		from: "allowNode",
		id: "replace-allownode-allowedtypes-and-disallowedtypes",
		to: "allowElement"
	},
	{
		from: "allowedTypes",
		id: "replace-allownode-allowedtypes-and-disallowedtypes",
		to: "allowedElements"
	},
	{
		from: "className",
		id: "remove-classname"
	},
	{
		from: "disallowedTypes",
		id: "replace-allownode-allowedtypes-and-disallowedtypes",
		to: "disallowedElements"
	},
	{
		from: "escapeHtml",
		id: "remove-buggy-html-in-markdown-parser"
	},
	{
		from: "includeElementIndex",
		id: "#remove-includeelementindex"
	},
	{
		from: "includeNodeIndex",
		id: "change-includenodeindex-to-includeelementindex"
	},
	{
		from: "linkTarget",
		id: "remove-linktarget"
	},
	{
		from: "plugins",
		id: "change-plugins-to-remarkplugins",
		to: "remarkPlugins"
	},
	{
		from: "rawSourcePos",
		id: "#remove-rawsourcepos"
	},
	{
		from: "renderers",
		id: "change-renderers-to-components",
		to: "components"
	},
	{
		from: "source",
		id: "change-source-to-children",
		to: "children"
	},
	{
		from: "sourcePos",
		id: "#remove-sourcepos"
	},
	{
		from: "transformImageUri",
		id: "#add-urltransform",
		to: "urlTransform"
	},
	{
		from: "transformLinkUri",
		id: "#add-urltransform",
		to: "urlTransform"
	}
];
function Ed(e) {
	let t = Dd(e), n = Od(e);
	return kd(t.runSync(t.parse(n), n), e);
}
function Dd(e) {
	let t = e.rehypePlugins || Y, n = e.remarkPlugins || Y, r = e.remarkRehypeOptions ? {
		...e.remarkRehypeOptions,
		...Cd
	} : Cd;
	return pd().use(El).use(n).use(zu, r).use(t);
}
function Od(e) {
	let t = e.children || "", n = new ad();
	return typeof t == "string" ? n.value = t : "" + t, n;
}
function kd(e, t) {
	let n = t.allowedElements, r = t.allowElement, i = t.components, a = t.disallowedElements, o = t.skipHtml, s = t.unwrapDisallowed, c = t.urlTransform || Ad;
	for (let e of Td) Object.hasOwn(t, e.from) && "" + e.from + (e.to ? "use `" + e.to + "` instead" : "remove it") + e.id;
	return ku(e, l), ro(e, {
		Fragment: J.Fragment,
		components: i,
		ignoreInvalidStyle: !0,
		jsx: J.jsx,
		jsxs: J.jsxs,
		passKeys: !0,
		passNode: !0
	});
	function l(e, t, i) {
		if (e.type === "raw" && i && typeof t == "number") return o ? i.children.splice(t, 1) : i.children[t] = {
			type: "text",
			value: e.value
		}, t;
		if (e.type === "element") {
			let t;
			for (t in To) if (Object.hasOwn(To, t) && Object.hasOwn(e.properties, t)) {
				let n = e.properties[t], r = To[t];
				(r === null || r.includes(e.tagName)) && (e.properties[t] = c(String(n || ""), t, e));
			}
		}
		if (e.type === "element") {
			let o = n ? !n.includes(e.tagName) : a ? a.includes(e.tagName) : !1;
			if (!o && r && typeof t == "number" && (o = !r(e, t, i)), o && i && typeof t == "number") return s && e.children ? i.children.splice(t, 1, ...e.children) : i.children.splice(t, 1), t;
		}
	}
}
function Ad(e) {
	let t = e.indexOf(":"), n = e.indexOf("?"), r = e.indexOf("#"), i = e.indexOf("/");
	return t === -1 || i !== -1 && t > i || n !== -1 && t > n || r !== -1 && t > r || wd.test(e.slice(0, t)) ? e : "";
}
//#endregion
//#region node_modules/ccount/index.js
function jd(e, t) {
	let n = String(e);
	if (typeof t != "string") throw TypeError("Expected character");
	let r = 0, i = n.indexOf(t);
	for (; i !== -1;) r++, i = n.indexOf(t, i + t.length);
	return r;
}
//#endregion
//#region node_modules/escape-string-regexp/index.js
function Md(e) {
	if (typeof e != "string") throw TypeError("Expected a string");
	return e.replace(/[|\\{}()[\]^$+*?.]/g, "\\$&").replace(/-/g, "\\x2d");
}
//#endregion
//#region node_modules/mdast-util-find-and-replace/lib/index.js
function Nd(e, t, n) {
	let r = vu((n || {}).ignore || []), i = Pd(t), a = -1;
	for (; ++a < i.length;) Du(e, "text", o);
	function o(e, t) {
		let n = -1, i;
		for (; ++n < t.length;) {
			let e = t[n], a = i ? i.children : void 0;
			if (r(e, a ? a.indexOf(e) : void 0, i)) return;
			i = e;
		}
		if (i) return s(e, t);
	}
	function s(e, t) {
		let n = t[t.length - 1], r = i[a][0], o = i[a][1], s = 0, c = n.children.indexOf(e), l = !1, u = [];
		r.lastIndex = 0;
		let d = r.exec(e.value);
		for (; d;) {
			let n = d.index, i = {
				index: d.index,
				input: d.input,
				stack: [...t, e]
			}, a = o(...d, i);
			if (typeof a == "string" && (a = a.length > 0 ? {
				type: "text",
				value: a
			} : void 0), a === !1 ? r.lastIndex = n + 1 : (s !== n && u.push({
				type: "text",
				value: e.value.slice(s, n)
			}), Array.isArray(a) ? u.push(...a) : a && u.push(a), s = n + d[0].length, l = !0), !r.global) break;
			d = r.exec(e.value);
		}
		return l ? (s < e.value.length && u.push({
			type: "text",
			value: e.value.slice(s)
		}), n.children.splice(c, 1, ...u)) : u = [e], c + u.length;
	}
}
function Pd(e) {
	let t = [];
	if (!Array.isArray(e)) throw TypeError("Expected find and replace tuple or list of tuples");
	let n = !e[0] || Array.isArray(e[0]) ? e : [e], r = -1;
	for (; ++r < n.length;) {
		let e = n[r];
		t.push([Fd(e[0]), Id(e[1])]);
	}
	return t;
}
function Fd(e) {
	return typeof e == "string" ? new RegExp(Md(e), "g") : e;
}
function Id(e) {
	return typeof e == "function" ? e : function() {
		return e;
	};
}
//#endregion
//#region node_modules/mdast-util-gfm-autolink-literal/lib/index.js
var Ld = "phrasing", Rd = [
	"autolink",
	"link",
	"image",
	"label"
];
function zd() {
	return {
		transforms: [qd],
		enter: {
			literalAutolink: Vd,
			literalAutolinkEmail: Hd,
			literalAutolinkHttp: Hd,
			literalAutolinkWww: Hd
		},
		exit: {
			literalAutolink: Kd,
			literalAutolinkEmail: Gd,
			literalAutolinkHttp: Ud,
			literalAutolinkWww: Wd
		}
	};
}
function Bd() {
	return { unsafe: [
		{
			character: "@",
			before: "[+\\-.\\w]",
			after: "[\\-.\\w]",
			inConstruct: Ld,
			notInConstruct: Rd
		},
		{
			character: ".",
			before: "[Ww]",
			after: "[\\-.\\w]",
			inConstruct: Ld,
			notInConstruct: Rd
		},
		{
			character: ":",
			before: "[ps]",
			after: "\\/",
			inConstruct: Ld,
			notInConstruct: Rd
		}
	] };
}
function Vd(e) {
	this.enter({
		type: "link",
		title: null,
		url: "",
		children: []
	}, e);
}
function Hd(e) {
	this.config.enter.autolinkProtocol.call(this, e);
}
function Ud(e) {
	this.config.exit.autolinkProtocol.call(this, e);
}
function Wd(e) {
	this.config.exit.data.call(this, e);
	let t = this.stack[this.stack.length - 1];
	t.type, t.url = "http://" + this.sliceSerialize(e);
}
function Gd(e) {
	this.config.exit.autolinkEmail.call(this, e);
}
function Kd(e) {
	this.exit(e);
}
function qd(e) {
	Nd(e, [[/(https?:\/\/|www(?=\.))([-.\w]+)([^ \t\r\n]*)/gi, Jd], [/(?<=^|\s|\p{P}|\p{S})([-.\w+]+)@([-\w]+(?:\.[-\w]+)+)/gu, Yd]], { ignore: ["link", "linkReference"] });
}
function Jd(e, t, n, r, i) {
	let a = "";
	if (!Qd(i) || (/^w/i.test(t) && (n = t + n, t = "", a = "http://"), !Xd(n))) return !1;
	let o = Zd(n + r);
	if (!o[0]) return !1;
	let s = {
		type: "link",
		title: null,
		url: a + t + o[0],
		children: [{
			type: "text",
			value: t + o[0]
		}]
	};
	return o[1] ? [s, {
		type: "text",
		value: o[1]
	}] : s;
}
function Yd(e, t, n, r) {
	return !Qd(r, !0) || /[-\d_]$/.test(n) ? !1 : {
		type: "link",
		title: null,
		url: "mailto:" + t + "@" + n,
		children: [{
			type: "text",
			value: t + "@" + n
		}]
	};
}
function Xd(e) {
	let t = e.split(".");
	return !(t.length < 2 || t[t.length - 1] && (/_/.test(t[t.length - 1]) || !/[a-zA-Z\d]/.test(t[t.length - 1])) || t[t.length - 2] && (/_/.test(t[t.length - 2]) || !/[a-zA-Z\d]/.test(t[t.length - 2])));
}
function Zd(e) {
	let t = /[!"&'),.:;<>?\]}]+$/.exec(e);
	if (!t) return [e, void 0];
	e = e.slice(0, t.index);
	let n = t[0], r = n.indexOf(")"), i = jd(e, "("), a = jd(e, ")");
	for (; r !== -1 && i > a;) e += n.slice(0, r + 1), n = n.slice(r + 1), r = n.indexOf(")"), a++;
	return [e, n];
}
function Qd(e, t) {
	let n = e.input.charCodeAt(e.index - 1);
	return (e.index === 0 || Qo(n) || Zo(n)) && (!t || n !== 47);
}
//#endregion
//#region node_modules/mdast-util-gfm-footnote/lib/index.js
lf.peek = cf;
function $d() {
	this.buffer();
}
function ef(e) {
	this.enter({
		type: "footnoteReference",
		identifier: "",
		label: ""
	}, e);
}
function tf() {
	this.buffer();
}
function nf(e) {
	this.enter({
		type: "footnoteDefinition",
		identifier: "",
		label: "",
		children: []
	}, e);
}
function rf(e) {
	let t = this.resume(), n = this.stack[this.stack.length - 1];
	n.type, n.identifier = Ho(this.sliceSerialize(e)).toLowerCase(), n.label = t;
}
function af(e) {
	this.exit(e);
}
function of(e) {
	let t = this.resume(), n = this.stack[this.stack.length - 1];
	n.type, n.identifier = Ho(this.sliceSerialize(e)).toLowerCase(), n.label = t;
}
function sf(e) {
	this.exit(e);
}
function cf() {
	return "[";
}
function lf(e, t, n, r) {
	let i = n.createTracker(r), a = i.move("[^"), o = n.enter("footnoteReference"), s = n.enter("reference");
	return a += i.move(n.safe(n.associationId(e), {
		after: "]",
		before: a
	})), s(), o(), a += i.move("]"), a;
}
function uf() {
	return {
		enter: {
			gfmFootnoteCallString: $d,
			gfmFootnoteCall: ef,
			gfmFootnoteDefinitionLabelString: tf,
			gfmFootnoteDefinition: nf
		},
		exit: {
			gfmFootnoteCallString: rf,
			gfmFootnoteCall: af,
			gfmFootnoteDefinitionLabelString: of,
			gfmFootnoteDefinition: sf
		}
	};
}
function df(e) {
	let t = !1;
	return e && e.firstLineBlank && (t = !0), {
		handlers: {
			footnoteDefinition: n,
			footnoteReference: lf
		},
		unsafe: [{
			character: "[",
			inConstruct: [
				"label",
				"phrasing",
				"reference"
			]
		}]
	};
	function n(e, n, r, i) {
		let a = r.createTracker(i), o = a.move("[^"), s = r.enter("footnoteDefinition"), c = r.enter("label");
		return o += a.move(r.safe(r.associationId(e), {
			before: o,
			after: "]"
		})), c(), o += a.move("]:"), e.children && e.children.length > 0 && (a.shift(4), o += a.move((t ? "\n" : " ") + r.indentLines(r.containerFlow(e, a.current()), t ? pf : ff))), s(), o;
	}
}
function ff(e, t, n) {
	return t === 0 ? e : pf(e, t, n);
}
function pf(e, t, n) {
	return (n ? "" : "    ") + e;
}
//#endregion
//#region node_modules/mdast-util-gfm-strikethrough/lib/index.js
var mf = [
	"autolink",
	"destinationLiteral",
	"destinationRaw",
	"reference",
	"titleQuote",
	"titleApostrophe"
];
yf.peek = bf;
function hf() {
	return {
		canContainEols: ["delete"],
		enter: { strikethrough: _f },
		exit: { strikethrough: vf }
	};
}
function gf() {
	return {
		unsafe: [{
			character: "~",
			inConstruct: "phrasing",
			notInConstruct: mf
		}],
		handlers: { delete: yf }
	};
}
function _f(e) {
	this.enter({
		type: "delete",
		children: []
	}, e);
}
function vf(e) {
	this.exit(e);
}
function yf(e, t, n, r) {
	let i = n.createTracker(r), a = n.enter("strikethrough"), o = i.move("~~");
	return o += n.containerPhrasing(e, {
		...i.current(),
		before: o,
		after: "~"
	}), o += i.move("~~"), a(), o;
}
function bf() {
	return "~";
}
//#endregion
//#region node_modules/markdown-table/index.js
function xf(e) {
	return e.length;
}
function Sf(e, t) {
	let n = t || {}, r = (n.align || []).concat(), i = n.stringLength || xf, a = [], o = [], s = [], c = [], l = 0, u = -1;
	for (; ++u < e.length;) {
		let t = [], r = [], a = -1;
		for (e[u].length > l && (l = e[u].length); ++a < e[u].length;) {
			let o = Cf(e[u][a]);
			if (n.alignDelimiters !== !1) {
				let e = i(o);
				r[a] = e, (c[a] === void 0 || e > c[a]) && (c[a] = e);
			}
			t.push(o);
		}
		o[u] = t, s[u] = r;
	}
	let d = -1;
	if (typeof r == "object" && "length" in r) for (; ++d < l;) a[d] = wf(r[d]);
	else {
		let e = wf(r);
		for (; ++d < l;) a[d] = e;
	}
	d = -1;
	let f = [], p = [];
	for (; ++d < l;) {
		let e = a[d], t = "", r = "";
		e === 99 ? (t = ":", r = ":") : e === 108 ? t = ":" : e === 114 && (r = ":");
		let i = n.alignDelimiters === !1 ? 1 : Math.max(1, c[d] - t.length - r.length), o = t + "-".repeat(i) + r;
		n.alignDelimiters !== !1 && (i = t.length + i + r.length, i > c[d] && (c[d] = i), p[d] = i), f[d] = o;
	}
	o.splice(1, 0, f), s.splice(1, 0, p), u = -1;
	let m = [];
	for (; ++u < o.length;) {
		let e = o[u], t = s[u];
		d = -1;
		let r = [];
		for (; ++d < l;) {
			let i = e[d] || "", o = "", s = "";
			if (n.alignDelimiters !== !1) {
				let e = c[d] - (t[d] || 0), n = a[d];
				n === 114 ? o = " ".repeat(e) : n === 99 ? e % 2 ? (o = " ".repeat(e / 2 + .5), s = " ".repeat(e / 2 - .5)) : (o = " ".repeat(e / 2), s = o) : s = " ".repeat(e);
			}
			n.delimiterStart !== !1 && !d && r.push("|"), n.padding !== !1 && !(n.alignDelimiters === !1 && i === "") && (n.delimiterStart !== !1 || d) && r.push(" "), n.alignDelimiters !== !1 && r.push(o), r.push(i), n.alignDelimiters !== !1 && r.push(s), n.padding !== !1 && r.push(" "), (n.delimiterEnd !== !1 || d !== l - 1) && r.push("|");
		}
		m.push(n.delimiterEnd === !1 ? r.join("").replace(/ +$/, "") : r.join(""));
	}
	return m.join("\n");
}
function Cf(e) {
	return e == null ? "" : String(e);
}
function wf(e) {
	let t = typeof e == "string" ? e.codePointAt(0) : 0;
	return t === 67 || t === 99 ? 99 : t === 76 || t === 108 ? 108 : t === 82 || t === 114 ? 114 : 0;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/blockquote.js
function Tf(e, t, n, r) {
	let i = n.enter("blockquote"), a = n.createTracker(r);
	a.move("> "), a.shift(2);
	let o = n.indentLines(n.containerFlow(e, a.current()), Ef);
	return i(), o;
}
function Ef(e, t, n) {
	return ">" + (n ? "" : " ") + e;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/pattern-in-scope.js
function Df(e, t) {
	return Of(e, t.inConstruct, !0) && !Of(e, t.notInConstruct, !1);
}
function Of(e, t, n) {
	if (typeof t == "string" && (t = [t]), !t || t.length === 0) return n;
	let r = -1;
	for (; ++r < t.length;) if (e.includes(t[r])) return !0;
	return !1;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/break.js
function kf(e, t, n, r) {
	let i = -1;
	for (; ++i < n.unsafe.length;) if (n.unsafe[i].character === "\n" && Df(n.stack, n.unsafe[i])) return /[ \t]/.test(r.before) ? "" : " ";
	return "\\\n";
}
//#endregion
//#region node_modules/longest-streak/index.js
function Af(e, t) {
	let n = String(e), r = n.indexOf(t), i = r, a = 0, o = 0;
	if (typeof t != "string") throw TypeError("Expected substring");
	for (; r !== -1;) r === i ? ++a > o && (o = a) : a = 1, i = r + t.length, r = n.indexOf(t, i);
	return o;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/format-code-as-indented.js
function jf(e, t) {
	return !!(t.options.fences === !1 && e.value && !e.lang && /[^ \r\n]/.test(e.value) && !/^[\t ]*(?:[\r\n]|$)|(?:^|[\r\n])[\t ]*$/.test(e.value));
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-fence.js
function Mf(e) {
	let t = e.options.fence || "`";
	if (t !== "`" && t !== "~") throw Error("Cannot serialize code with `" + t + "` for `options.fence`, expected `` ` `` or `~`");
	return t;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/code.js
function Nf(e, t, n, r) {
	let i = Mf(n), a = e.value || "", o = i === "`" ? "GraveAccent" : "Tilde";
	if (jf(e, n)) {
		let e = n.enter("codeIndented"), t = n.indentLines(a, Pf);
		return e(), t;
	}
	let s = n.createTracker(r), c = i.repeat(Math.max(Af(a, i) + 1, 3)), l = n.enter("codeFenced"), u = s.move(c);
	if (e.lang) {
		let t = n.enter(`codeFencedLang${o}`);
		u += s.move(n.safe(e.lang, {
			before: u,
			after: " ",
			encode: ["`"],
			...s.current()
		})), t();
	}
	if (e.lang && e.meta) {
		let t = n.enter(`codeFencedMeta${o}`);
		u += s.move(" "), u += s.move(n.safe(e.meta, {
			before: u,
			after: "\n",
			encode: ["`"],
			...s.current()
		})), t();
	}
	return u += s.move("\n"), a && (u += s.move(a + "\n")), u += s.move(c), l(), u;
}
function Pf(e, t, n) {
	return (n ? "" : "    ") + e;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-quote.js
function Ff(e) {
	let t = e.options.quote || "\"";
	if (t !== "\"" && t !== "'") throw Error("Cannot serialize title with `" + t + "` for `options.quote`, expected `\"`, or `'`");
	return t;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/definition.js
function If(e, t, n, r) {
	let i = Ff(n), a = i === "\"" ? "Quote" : "Apostrophe", o = n.enter("definition"), s = n.enter("label"), c = n.createTracker(r), l = c.move("[");
	return l += c.move(n.safe(n.associationId(e), {
		before: l,
		after: "]",
		...c.current()
	})), l += c.move("]: "), s(), !e.url || /[\0- \u007F]/.test(e.url) ? (s = n.enter("destinationLiteral"), l += c.move("<"), l += c.move(n.safe(e.url, {
		before: l,
		after: ">",
		...c.current()
	})), l += c.move(">")) : (s = n.enter("destinationRaw"), l += c.move(n.safe(e.url, {
		before: l,
		after: e.title ? " " : "\n",
		...c.current()
	}))), s(), e.title && (s = n.enter(`title${a}`), l += c.move(" " + i), l += c.move(n.safe(e.title, {
		before: l,
		after: i,
		...c.current()
	})), l += c.move(i), s()), o(), l;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-emphasis.js
function Lf(e) {
	let t = e.options.emphasis || "*";
	if (t !== "*" && t !== "_") throw Error("Cannot serialize emphasis with `" + t + "` for `options.emphasis`, expected `*`, or `_`");
	return t;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/encode-character-reference.js
function Rf(e) {
	return "&#x" + e.toString(16).toUpperCase() + ";";
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/encode-info.js
function zf(e, t, n) {
	let r = ss(e), i = ss(t);
	return r === void 0 ? i === void 0 ? n === "_" ? {
		inside: !0,
		outside: !0
	} : {
		inside: !1,
		outside: !1
	} : i === 1 ? {
		inside: !0,
		outside: !0
	} : {
		inside: !1,
		outside: !0
	} : r === 1 ? i === void 0 ? {
		inside: !1,
		outside: !1
	} : i === 1 ? {
		inside: !0,
		outside: !0
	} : {
		inside: !1,
		outside: !1
	} : i === void 0 ? {
		inside: !1,
		outside: !1
	} : i === 1 ? {
		inside: !0,
		outside: !1
	} : {
		inside: !1,
		outside: !1
	};
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/emphasis.js
Bf.peek = Vf;
function Bf(e, t, n, r) {
	let i = Lf(n), a = n.enter("emphasis"), o = n.createTracker(r), s = o.move(i), c = o.move(n.containerPhrasing(e, {
		after: i,
		before: s,
		...o.current()
	})), l = c.charCodeAt(0), u = zf(r.before.charCodeAt(r.before.length - 1), l, i);
	u.inside && (c = Rf(l) + c.slice(1));
	let d = c.charCodeAt(c.length - 1), f = zf(r.after.charCodeAt(0), d, i);
	f.inside && (c = c.slice(0, -1) + Rf(d));
	let p = o.move(i);
	return a(), n.attentionEncodeSurroundingInfo = {
		after: f.outside,
		before: u.outside
	}, s + c + p;
}
function Vf(e, t, n) {
	return n.options.emphasis || "*";
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/format-heading-as-setext.js
function Hf(e, t) {
	let n = !1;
	return ku(e, function(e) {
		if ("value" in e && /\r?\n|\r/.test(e.value) || e.type === "break") return n = !0, !1;
	}), !!((!e.depth || e.depth < 3) && ko(e) && (t.options.setext || n));
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/heading.js
function Uf(e, t, n, r) {
	let i = Math.max(Math.min(6, e.depth || 1), 1), a = n.createTracker(r);
	if (Hf(e, n)) {
		let t = n.enter("headingSetext"), r = n.enter("phrasing"), o = n.containerPhrasing(e, {
			...a.current(),
			before: "\n",
			after: "\n"
		});
		return r(), t(), o + "\n" + (i === 1 ? "=" : "-").repeat(o.length - (Math.max(o.lastIndexOf("\r"), o.lastIndexOf("\n")) + 1));
	}
	let o = "#".repeat(i), s = n.enter("headingAtx"), c = n.enter("phrasing");
	a.move(o + " ");
	let l = n.containerPhrasing(e, {
		before: "# ",
		after: "\n",
		...a.current()
	});
	return /^[\t ]/.test(l) && (l = Rf(l.charCodeAt(0)) + l.slice(1)), l = l ? o + " " + l : o, n.options.closeAtx && (l += " " + o), c(), s(), l;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/html.js
Wf.peek = Gf;
function Wf(e) {
	return e.value || "";
}
function Gf() {
	return "<";
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/image.js
Kf.peek = qf;
function Kf(e, t, n, r) {
	let i = Ff(n), a = i === "\"" ? "Quote" : "Apostrophe", o = n.enter("image"), s = n.enter("label"), c = n.createTracker(r), l = c.move("![");
	return l += c.move(n.safe(e.alt, {
		before: l,
		after: "]",
		...c.current()
	})), l += c.move("]("), s(), !e.url && e.title || /[\0- \u007F]/.test(e.url) ? (s = n.enter("destinationLiteral"), l += c.move("<"), l += c.move(n.safe(e.url, {
		before: l,
		after: ">",
		...c.current()
	})), l += c.move(">")) : (s = n.enter("destinationRaw"), l += c.move(n.safe(e.url, {
		before: l,
		after: e.title ? " " : ")",
		...c.current()
	}))), s(), e.title && (s = n.enter(`title${a}`), l += c.move(" " + i), l += c.move(n.safe(e.title, {
		before: l,
		after: i,
		...c.current()
	})), l += c.move(i), s()), l += c.move(")"), o(), l;
}
function qf() {
	return "!";
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/image-reference.js
Jf.peek = Yf;
function Jf(e, t, n, r) {
	let i = e.referenceType, a = n.enter("imageReference"), o = n.enter("label"), s = n.createTracker(r), c = s.move("!["), l = n.safe(e.alt, {
		before: c,
		after: "]",
		...s.current()
	});
	c += s.move(l + "]["), o();
	let u = n.stack;
	n.stack = [], o = n.enter("reference");
	let d = n.safe(n.associationId(e), {
		before: c,
		after: "]",
		...s.current()
	});
	return o(), n.stack = u, a(), i === "full" || !l || l !== d ? c += s.move(d + "]") : i === "shortcut" ? c = c.slice(0, -1) : c += s.move("]"), c;
}
function Yf() {
	return "!";
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/inline-code.js
Xf.peek = Zf;
function Xf(e, t, n) {
	let r = e.value || "", i = "`", a = -1;
	for (; RegExp("(^|[^`])" + i + "([^`]|$)").test(r);) i += "`";
	for (/[^ \r\n]/.test(r) && (/^[ \r\n]/.test(r) && /[ \r\n]$/.test(r) || /^`|`$/.test(r)) && (r = " " + r + " "); ++a < n.unsafe.length;) {
		let e = n.unsafe[a], t = n.compilePattern(e), i;
		if (e.atBreak) for (; i = t.exec(r);) {
			let e = i.index;
			r.charCodeAt(e) === 10 && r.charCodeAt(e - 1) === 13 && e--, r = r.slice(0, e) + " " + r.slice(i.index + 1);
		}
	}
	return i + r + i;
}
function Zf() {
	return "`";
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/format-link-as-autolink.js
function Qf(e, t) {
	let n = ko(e);
	return !!(!t.options.resourceLink && e.url && !e.title && e.children && e.children.length === 1 && e.children[0].type === "text" && (n === e.url || "mailto:" + n === e.url) && /^[a-z][a-z+.-]+:/i.test(e.url) && !/[\0- <>\u007F]/.test(e.url));
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/link.js
$f.peek = ep;
function $f(e, t, n, r) {
	let i = Ff(n), a = i === "\"" ? "Quote" : "Apostrophe", o = n.createTracker(r), s, c;
	if (Qf(e, n)) {
		let t = n.stack;
		n.stack = [], s = n.enter("autolink");
		let r = o.move("<");
		return r += o.move(n.containerPhrasing(e, {
			before: r,
			after: ">",
			...o.current()
		})), r += o.move(">"), s(), n.stack = t, r;
	}
	s = n.enter("link"), c = n.enter("label");
	let l = o.move("[");
	return l += o.move(n.containerPhrasing(e, {
		before: l,
		after: "](",
		...o.current()
	})), l += o.move("]("), c(), !e.url && e.title || /[\0- \u007F]/.test(e.url) ? (c = n.enter("destinationLiteral"), l += o.move("<"), l += o.move(n.safe(e.url, {
		before: l,
		after: ">",
		...o.current()
	})), l += o.move(">")) : (c = n.enter("destinationRaw"), l += o.move(n.safe(e.url, {
		before: l,
		after: e.title ? " " : ")",
		...o.current()
	}))), c(), e.title && (c = n.enter(`title${a}`), l += o.move(" " + i), l += o.move(n.safe(e.title, {
		before: l,
		after: i,
		...o.current()
	})), l += o.move(i), c()), l += o.move(")"), s(), l;
}
function ep(e, t, n) {
	return Qf(e, n) ? "<" : "[";
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/link-reference.js
tp.peek = np;
function tp(e, t, n, r) {
	let i = e.referenceType, a = n.enter("linkReference"), o = n.enter("label"), s = n.createTracker(r), c = s.move("["), l = n.containerPhrasing(e, {
		before: c,
		after: "]",
		...s.current()
	});
	c += s.move(l + "]["), o();
	let u = n.stack;
	n.stack = [], o = n.enter("reference");
	let d = n.safe(n.associationId(e), {
		before: c,
		after: "]",
		...s.current()
	});
	return o(), n.stack = u, a(), i === "full" || !l || l !== d ? c += s.move(d + "]") : i === "shortcut" ? c = c.slice(0, -1) : c += s.move("]"), c;
}
function np() {
	return "[";
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-bullet.js
function rp(e) {
	let t = e.options.bullet || "*";
	if (t !== "*" && t !== "+" && t !== "-") throw Error("Cannot serialize items with `" + t + "` for `options.bullet`, expected `*`, `+`, or `-`");
	return t;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-bullet-other.js
function ip(e) {
	let t = rp(e), n = e.options.bulletOther;
	if (!n) return t === "*" ? "-" : "*";
	if (n !== "*" && n !== "+" && n !== "-") throw Error("Cannot serialize items with `" + n + "` for `options.bulletOther`, expected `*`, `+`, or `-`");
	if (n === t) throw Error("Expected `bullet` (`" + t + "`) and `bulletOther` (`" + n + "`) to be different");
	return n;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-bullet-ordered.js
function ap(e) {
	let t = e.options.bulletOrdered || ".";
	if (t !== "." && t !== ")") throw Error("Cannot serialize items with `" + t + "` for `options.bulletOrdered`, expected `.` or `)`");
	return t;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-rule.js
function op(e) {
	let t = e.options.rule || "*";
	if (t !== "*" && t !== "-" && t !== "_") throw Error("Cannot serialize rules with `" + t + "` for `options.rule`, expected `*`, `-`, or `_`");
	return t;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/list.js
function sp(e, t, n, r) {
	let i = n.enter("list"), a = n.bulletCurrent, o = e.ordered ? ap(n) : rp(n), s = e.ordered ? o === "." ? ")" : "." : ip(n), c = t && n.bulletLastUsed ? o === n.bulletLastUsed : !1;
	if (!e.ordered) {
		let t = e.children ? e.children[0] : void 0;
		if ((o === "*" || o === "-") && t && (!t.children || !t.children[0]) && n.stack[n.stack.length - 1] === "list" && n.stack[n.stack.length - 2] === "listItem" && n.stack[n.stack.length - 3] === "list" && n.stack[n.stack.length - 4] === "listItem" && n.indexStack[n.indexStack.length - 1] === 0 && n.indexStack[n.indexStack.length - 2] === 0 && n.indexStack[n.indexStack.length - 3] === 0 && (c = !0), op(n) === o && t) {
			let t = -1;
			for (; ++t < e.children.length;) {
				let n = e.children[t];
				if (n && n.type === "listItem" && n.children && n.children[0] && n.children[0].type === "thematicBreak") {
					c = !0;
					break;
				}
			}
		}
	}
	c && (o = s), n.bulletCurrent = o;
	let l = n.containerFlow(e, r);
	return n.bulletLastUsed = o, n.bulletCurrent = a, i(), l;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-list-item-indent.js
function cp(e) {
	let t = e.options.listItemIndent || "one";
	if (t !== "tab" && t !== "one" && t !== "mixed") throw Error("Cannot serialize items with `" + t + "` for `options.listItemIndent`, expected `tab`, `one`, or `mixed`");
	return t;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/list-item.js
function lp(e, t, n, r) {
	let i = cp(n), a = n.bulletCurrent || rp(n);
	t && t.type === "list" && t.ordered && (a = (typeof t.start == "number" && t.start > -1 ? t.start : 1) + (n.options.incrementListMarker === !1 ? 0 : t.children.indexOf(e)) + a);
	let o = a.length + 1;
	(i === "tab" || i === "mixed" && (t && t.type === "list" && t.spread || e.spread)) && (o = Math.ceil(o / 4) * 4);
	let s = n.createTracker(r);
	s.move(a + " ".repeat(o - a.length)), s.shift(o);
	let c = n.enter("listItem"), l = n.indentLines(n.containerFlow(e, s.current()), u);
	return c(), l;
	function u(e, t, n) {
		return t ? (n ? "" : " ".repeat(o)) + e : (n ? a : a + " ".repeat(o - a.length)) + e;
	}
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/paragraph.js
function up(e, t, n, r) {
	let i = n.enter("paragraph"), a = n.enter("phrasing"), o = n.containerPhrasing(e, r);
	return a(), i(), o;
}
//#endregion
//#region node_modules/mdast-util-phrasing/lib/index.js
var dp = vu([
	"break",
	"delete",
	"emphasis",
	"footnote",
	"footnoteReference",
	"image",
	"imageReference",
	"inlineCode",
	"inlineMath",
	"link",
	"linkReference",
	"mdxJsxTextElement",
	"mdxTextExpression",
	"strong",
	"text",
	"textDirective"
]);
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/root.js
function fp(e, t, n, r) {
	return (e.children.some(function(e) {
		return dp(e);
	}) ? n.containerPhrasing : n.containerFlow).call(n, e, r);
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-strong.js
function pp(e) {
	let t = e.options.strong || "*";
	if (t !== "*" && t !== "_") throw Error("Cannot serialize strong with `" + t + "` for `options.strong`, expected `*`, or `_`");
	return t;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/strong.js
mp.peek = hp;
function mp(e, t, n, r) {
	let i = pp(n), a = n.enter("strong"), o = n.createTracker(r), s = o.move(i + i), c = o.move(n.containerPhrasing(e, {
		after: i,
		before: s,
		...o.current()
	})), l = c.charCodeAt(0), u = zf(r.before.charCodeAt(r.before.length - 1), l, i);
	u.inside && (c = Rf(l) + c.slice(1));
	let d = c.charCodeAt(c.length - 1), f = zf(r.after.charCodeAt(0), d, i);
	f.inside && (c = c.slice(0, -1) + Rf(d));
	let p = o.move(i + i);
	return a(), n.attentionEncodeSurroundingInfo = {
		after: f.outside,
		before: u.outside
	}, s + c + p;
}
function hp(e, t, n) {
	return n.options.strong || "*";
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/text.js
function gp(e, t, n, r) {
	return n.safe(e.value, r);
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/util/check-rule-repetition.js
function _p(e) {
	let t = e.options.ruleRepetition || 3;
	if (t < 3) throw Error("Cannot serialize rules with repetition `" + t + "` for `options.ruleRepetition`, expected `3` or more");
	return t;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/thematic-break.js
function vp(e, t, n) {
	let r = (op(n) + (n.options.ruleSpaces ? " " : "")).repeat(_p(n));
	return n.options.ruleSpaces ? r.slice(0, -1) : r;
}
//#endregion
//#region node_modules/mdast-util-to-markdown/lib/handle/index.js
var yp = {
	blockquote: Tf,
	break: kf,
	code: Nf,
	definition: If,
	emphasis: Bf,
	hardBreak: kf,
	heading: Uf,
	html: Wf,
	image: Kf,
	imageReference: Jf,
	inlineCode: Xf,
	link: $f,
	linkReference: tp,
	list: sp,
	listItem: lp,
	paragraph: up,
	root: fp,
	strong: mp,
	text: gp,
	thematicBreak: vp
};
//#endregion
//#region node_modules/mdast-util-gfm-table/lib/index.js
function bp() {
	return {
		enter: {
			table: xp,
			tableData: Tp,
			tableHeader: Tp,
			tableRow: Cp
		},
		exit: {
			codeText: Ep,
			table: Sp,
			tableData: wp,
			tableHeader: wp,
			tableRow: wp
		}
	};
}
function xp(e) {
	let t = e._align;
	this.enter({
		type: "table",
		align: t.map(function(e) {
			return e === "none" ? null : e;
		}),
		children: []
	}, e), this.data.inTable = !0;
}
function Sp(e) {
	this.exit(e), this.data.inTable = void 0;
}
function Cp(e) {
	this.enter({
		type: "tableRow",
		children: []
	}, e);
}
function wp(e) {
	this.exit(e);
}
function Tp(e) {
	this.enter({
		type: "tableCell",
		children: []
	}, e);
}
function Ep(e) {
	let t = this.resume();
	this.data.inTable && (t = t.replace(/\\([\\|])/g, Dp));
	let n = this.stack[this.stack.length - 1];
	n.type, n.value = t, this.exit(e);
}
function Dp(e, t) {
	return t === "|" ? t : e;
}
function Op(e) {
	let t = e || {}, n = t.tableCellPadding, r = t.tablePipeAlign, i = t.stringLength, a = n ? " " : "|";
	return {
		unsafe: [
			{
				character: "\r",
				inConstruct: "tableCell"
			},
			{
				character: "\n",
				inConstruct: "tableCell"
			},
			{
				atBreak: !0,
				character: "|",
				after: "[	 :-]"
			},
			{
				character: "|",
				inConstruct: "tableCell"
			},
			{
				atBreak: !0,
				character: ":",
				after: "-"
			},
			{
				atBreak: !0,
				character: "-",
				after: "[:|-]"
			}
		],
		handlers: {
			inlineCode: f,
			table: o,
			tableCell: c,
			tableRow: s
		}
	};
	function o(e, t, n, r) {
		return l(u(e, n, r), e.align);
	}
	function s(e, t, n, r) {
		let i = l([d(e, n, r)]);
		return i.slice(0, i.indexOf("\n"));
	}
	function c(e, t, n, r) {
		let i = n.enter("tableCell"), o = n.enter("phrasing"), s = n.containerPhrasing(e, {
			...r,
			before: a,
			after: a
		});
		return o(), i(), s;
	}
	function l(e, t) {
		return Sf(e, {
			align: t,
			alignDelimiters: r,
			padding: n,
			stringLength: i
		});
	}
	function u(e, t, n) {
		let r = e.children, i = -1, a = [], o = t.enter("table");
		for (; ++i < r.length;) a[i] = d(r[i], t, n);
		return o(), a;
	}
	function d(e, t, n) {
		let r = e.children, i = -1, a = [], o = t.enter("tableRow");
		for (; ++i < r.length;) a[i] = c(r[i], e, t, n);
		return o(), a;
	}
	function f(e, t, n) {
		let r = yp.inlineCode(e, t, n);
		return n.stack.includes("tableCell") && (r = r.replace(/\|/g, "\\$&")), r;
	}
}
//#endregion
//#region node_modules/mdast-util-gfm-task-list-item/lib/index.js
function kp() {
	return { exit: {
		taskListCheckValueChecked: jp,
		taskListCheckValueUnchecked: jp,
		paragraph: Mp
	} };
}
function Ap() {
	return {
		unsafe: [{
			atBreak: !0,
			character: "-",
			after: "[:|-]"
		}],
		handlers: { listItem: Np }
	};
}
function jp(e) {
	let t = this.stack[this.stack.length - 2];
	t.type, t.checked = e.type === "taskListCheckValueChecked";
}
function Mp(e) {
	let t = this.stack[this.stack.length - 2];
	if (t && t.type === "listItem" && typeof t.checked == "boolean") {
		let e = this.stack[this.stack.length - 1];
		e.type;
		let n = e.children[0];
		if (n && n.type === "text") {
			let r = t.children, i = -1, a;
			for (; ++i < r.length;) {
				let e = r[i];
				if (e.type === "paragraph") {
					a = e;
					break;
				}
			}
			a === e && (n.value = n.value.slice(1), n.value.length === 0 ? e.children.shift() : e.position && n.position && typeof n.position.start.offset == "number" && (n.position.start.column++, n.position.start.offset++, e.position.start = Object.assign({}, n.position.start)));
		}
	}
	this.exit(e);
}
function Np(e, t, n, r) {
	let i = e.children[0], a = typeof e.checked == "boolean" && i && i.type === "paragraph", o = "[" + (e.checked ? "x" : " ") + "] ", s = n.createTracker(r);
	a && s.move(o);
	let c = yp.listItem(e, t, n, {
		...r,
		...s.current()
	});
	return a && (c = c.replace(/^(?:[*+-]|\d+\.)([\r\n]| {1,3})/, l)), c;
	function l(e) {
		return e + o;
	}
}
//#endregion
//#region node_modules/mdast-util-gfm/lib/index.js
function Pp() {
	return [
		zd(),
		uf(),
		hf(),
		bp(),
		kp()
	];
}
function Fp(e) {
	return { extensions: [
		Bd(),
		df(e),
		gf(),
		Op(e),
		Ap()
	] };
}
//#endregion
//#region node_modules/micromark-extension-gfm-autolink-literal/lib/syntax.js
var Ip = {
	tokenize: Xp,
	partial: !0
}, Lp = {
	tokenize: Zp,
	partial: !0
}, Rp = {
	tokenize: Qp,
	partial: !0
}, zp = {
	tokenize: $p,
	partial: !0
}, Bp = {
	tokenize: em,
	partial: !0
}, Vp = {
	name: "wwwAutolink",
	tokenize: Jp,
	previous: tm
}, Hp = {
	name: "protocolAutolink",
	tokenize: Yp,
	previous: nm
}, Up = {
	name: "emailAutolink",
	tokenize: qp,
	previous: rm
}, Wp = {};
function Gp() {
	return { text: Wp };
}
for (var Kp = 48; Kp < 123;) Wp[Kp] = Up, Kp++, Kp === 58 ? Kp = 65 : Kp === 91 && (Kp = 97);
Wp[43] = Up, Wp[45] = Up, Wp[46] = Up, Wp[95] = Up, Wp[72] = [Up, Hp], Wp[104] = [Up, Hp], Wp[87] = [Up, Vp], Wp[119] = [Up, Vp];
function qp(e, t, n) {
	let r = this, i, a;
	return o;
	function o(t) {
		return !im(t) || !rm.call(r, r.previous) || am(r.events) ? n(t) : (e.enter("literalAutolink"), e.enter("literalAutolinkEmail"), s(t));
	}
	function s(t) {
		return im(t) ? (e.consume(t), s) : t === 64 ? (e.consume(t), c) : n(t);
	}
	function c(t) {
		return t === 46 ? e.check(Bp, u, l)(t) : t === 45 || t === 95 || Wo(t) ? (a = !0, e.consume(t), c) : u(t);
	}
	function l(t) {
		return e.consume(t), i = !0, c;
	}
	function u(o) {
		return a && i && Uo(r.previous) ? (e.exit("literalAutolinkEmail"), e.exit("literalAutolink"), t(o)) : n(o);
	}
}
function Jp(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return t !== 87 && t !== 119 || !tm.call(r, r.previous) || am(r.events) ? n(t) : (e.enter("literalAutolink"), e.enter("literalAutolinkWww"), e.check(Ip, e.attempt(Lp, e.attempt(Rp, a), n), n)(t));
	}
	function a(n) {
		return e.exit("literalAutolinkWww"), e.exit("literalAutolink"), t(n);
	}
}
function Yp(e, t, n) {
	let r = this, i = "", a = !1;
	return o;
	function o(t) {
		return (t === 72 || t === 104) && nm.call(r, r.previous) && !am(r.events) ? (e.enter("literalAutolink"), e.enter("literalAutolinkHttp"), i += String.fromCodePoint(t), e.consume(t), s) : n(t);
	}
	function s(t) {
		if (Uo(t) && i.length < 5) return i += String.fromCodePoint(t), e.consume(t), s;
		if (t === 58) {
			let n = i.toLowerCase();
			if (n === "http" || n === "https") return e.consume(t), c;
		}
		return n(t);
	}
	function c(t) {
		return t === 47 ? (e.consume(t), a ? l : (a = !0, c)) : n(t);
	}
	function l(t) {
		return t === null || Ko(t) || Xo(t) || Qo(t) || Zo(t) ? n(t) : e.attempt(Lp, e.attempt(Rp, u), n)(t);
	}
	function u(n) {
		return e.exit("literalAutolinkHttp"), e.exit("literalAutolink"), t(n);
	}
}
function Xp(e, t, n) {
	let r = 0;
	return i;
	function i(t) {
		return (t === 87 || t === 119) && r < 3 ? (r++, e.consume(t), i) : t === 46 && r === 3 ? (e.consume(t), a) : n(t);
	}
	function a(e) {
		return e === null ? n(e) : t(e);
	}
}
function Zp(e, t, n) {
	let r, i, a;
	return o;
	function o(t) {
		return t === 46 || t === 95 ? e.check(zp, c, s)(t) : t === null || Xo(t) || Qo(t) || t !== 45 && Zo(t) ? c(t) : (a = !0, e.consume(t), o);
	}
	function s(t) {
		return t === 95 ? r = !0 : (i = r, r = void 0), e.consume(t), o;
	}
	function c(e) {
		return i || r || !a ? n(e) : t(e);
	}
}
function Qp(e, t) {
	let n = 0, r = 0;
	return i;
	function i(o) {
		return o === 40 ? (n++, e.consume(o), i) : o === 41 && r < n ? a(o) : o === 33 || o === 34 || o === 38 || o === 39 || o === 41 || o === 42 || o === 44 || o === 46 || o === 58 || o === 59 || o === 60 || o === 63 || o === 93 || o === 95 || o === 126 ? e.check(zp, t, a)(o) : o === null || Xo(o) || Qo(o) ? t(o) : (e.consume(o), i);
	}
	function a(t) {
		return t === 41 && r++, e.consume(t), i;
	}
}
function $p(e, t, n) {
	return r;
	function r(o) {
		return o === 33 || o === 34 || o === 39 || o === 41 || o === 42 || o === 44 || o === 46 || o === 58 || o === 59 || o === 63 || o === 95 || o === 126 ? (e.consume(o), r) : o === 38 ? (e.consume(o), a) : o === 93 ? (e.consume(o), i) : o === 60 || o === null || Xo(o) || Qo(o) ? t(o) : n(o);
	}
	function i(e) {
		return e === null || e === 40 || e === 91 || Xo(e) || Qo(e) ? t(e) : r(e);
	}
	function a(e) {
		return Uo(e) ? o(e) : n(e);
	}
	function o(t) {
		return t === 59 ? (e.consume(t), r) : Uo(t) ? (e.consume(t), o) : n(t);
	}
}
function em(e, t, n) {
	return r;
	function r(t) {
		return e.consume(t), i;
	}
	function i(e) {
		return Wo(e) ? n(e) : t(e);
	}
}
function tm(e) {
	return e === null || e === 40 || e === 42 || e === 95 || e === 91 || e === 93 || e === 126 || Xo(e);
}
function nm(e) {
	return !Uo(e);
}
function rm(e) {
	return !(e === 47 || im(e));
}
function im(e) {
	return e === 43 || e === 45 || e === 46 || e === 95 || Wo(e);
}
function am(e) {
	let t = e.length, n = !1;
	for (; t--;) {
		let r = e[t][1];
		if ((r.type === "labelLink" || r.type === "labelImage") && !r._balanced) {
			n = !0;
			break;
		}
		if (r._gfmAutolinkLiteralWalkedInto) {
			n = !1;
			break;
		}
	}
	return e.length > 0 && !n && (e[e.length - 1][1]._gfmAutolinkLiteralWalkedInto = !0), n;
}
//#endregion
//#region node_modules/micromark-extension-gfm-footnote/lib/syntax.js
var om = {
	tokenize: mm,
	partial: !0
};
function sm() {
	return {
		document: { 91: {
			name: "gfmFootnoteDefinition",
			tokenize: dm,
			continuation: { tokenize: fm },
			exit: pm
		} },
		text: {
			91: {
				name: "gfmFootnoteCall",
				tokenize: um
			},
			93: {
				name: "gfmPotentialFootnoteCall",
				add: "after",
				tokenize: cm,
				resolveTo: lm
			}
		}
	};
}
function cm(e, t, n) {
	let r = this, i = r.events.length, a = r.parser.gfmFootnotes || (r.parser.gfmFootnotes = []), o;
	for (; i--;) {
		let e = r.events[i][1];
		if (e.type === "labelImage") {
			o = e;
			break;
		}
		if (e.type === "gfmFootnoteCall" || e.type === "labelLink" || e.type === "label" || e.type === "image" || e.type === "link") break;
	}
	return s;
	function s(i) {
		if (!o || !o._balanced) return n(i);
		let s = Ho(r.sliceSerialize({
			start: o.end,
			end: r.now()
		}));
		return s.codePointAt(0) !== 94 || !a.includes(s.slice(1)) ? n(i) : (e.enter("gfmFootnoteCallLabelMarker"), e.consume(i), e.exit("gfmFootnoteCallLabelMarker"), t(i));
	}
}
function lm(e, t) {
	let n = e.length;
	for (; n--;) if (e[n][1].type === "labelImage" && e[n][0] === "enter") {
		e[n][1];
		break;
	}
	e[n + 1][1].type = "data", e[n + 3][1].type = "gfmFootnoteCallLabelMarker";
	let r = {
		type: "gfmFootnoteCall",
		start: Object.assign({}, e[n + 3][1].start),
		end: Object.assign({}, e[e.length - 1][1].end)
	}, i = {
		type: "gfmFootnoteCallMarker",
		start: Object.assign({}, e[n + 3][1].end),
		end: Object.assign({}, e[n + 3][1].end)
	};
	i.end.column++, i.end.offset++, i.end._bufferIndex++;
	let a = {
		type: "gfmFootnoteCallString",
		start: Object.assign({}, i.end),
		end: Object.assign({}, e[e.length - 1][1].start)
	}, o = {
		type: "chunkString",
		contentType: "string",
		start: Object.assign({}, a.start),
		end: Object.assign({}, a.end)
	}, s = [
		e[n + 1],
		e[n + 2],
		[
			"enter",
			r,
			t
		],
		e[n + 3],
		e[n + 4],
		[
			"enter",
			i,
			t
		],
		[
			"exit",
			i,
			t
		],
		[
			"enter",
			a,
			t
		],
		[
			"enter",
			o,
			t
		],
		[
			"exit",
			o,
			t
		],
		[
			"exit",
			a,
			t
		],
		e[e.length - 2],
		e[e.length - 1],
		[
			"exit",
			r,
			t
		]
	];
	return e.splice(n, e.length - n + 1, ...s), e;
}
function um(e, t, n) {
	let r = this, i = r.parser.gfmFootnotes || (r.parser.gfmFootnotes = []), a = 0, o;
	return s;
	function s(t) {
		return e.enter("gfmFootnoteCall"), e.enter("gfmFootnoteCallLabelMarker"), e.consume(t), e.exit("gfmFootnoteCallLabelMarker"), c;
	}
	function c(t) {
		return t === 94 ? (e.enter("gfmFootnoteCallMarker"), e.consume(t), e.exit("gfmFootnoteCallMarker"), e.enter("gfmFootnoteCallString"), e.enter("chunkString").contentType = "string", l) : n(t);
	}
	function l(s) {
		if (a > 999 || s === 93 && !o || s === null || s === 91 || Xo(s)) return n(s);
		if (s === 93) {
			e.exit("chunkString");
			let a = e.exit("gfmFootnoteCallString");
			return i.includes(Ho(r.sliceSerialize(a))) ? (e.enter("gfmFootnoteCallLabelMarker"), e.consume(s), e.exit("gfmFootnoteCallLabelMarker"), e.exit("gfmFootnoteCall"), t) : n(s);
		}
		return Xo(s) || (o = !0), a++, e.consume(s), s === 92 ? u : l;
	}
	function u(t) {
		return t === 91 || t === 92 || t === 93 ? (e.consume(t), a++, l) : l(t);
	}
}
function dm(e, t, n) {
	let r = this, i = r.parser.gfmFootnotes || (r.parser.gfmFootnotes = []), a, o = 0, s;
	return c;
	function c(t) {
		return e.enter("gfmFootnoteDefinition")._container = !0, e.enter("gfmFootnoteDefinitionLabel"), e.enter("gfmFootnoteDefinitionLabelMarker"), e.consume(t), e.exit("gfmFootnoteDefinitionLabelMarker"), l;
	}
	function l(t) {
		return t === 94 ? (e.enter("gfmFootnoteDefinitionMarker"), e.consume(t), e.exit("gfmFootnoteDefinitionMarker"), e.enter("gfmFootnoteDefinitionLabelString"), e.enter("chunkString").contentType = "string", u) : n(t);
	}
	function u(t) {
		if (o > 999 || t === 93 && !s || t === null || t === 91 || Xo(t)) return n(t);
		if (t === 93) {
			e.exit("chunkString");
			let n = e.exit("gfmFootnoteDefinitionLabelString");
			return a = Ho(r.sliceSerialize(n)), e.enter("gfmFootnoteDefinitionLabelMarker"), e.consume(t), e.exit("gfmFootnoteDefinitionLabelMarker"), e.exit("gfmFootnoteDefinitionLabel"), f;
		}
		return Xo(t) || (s = !0), o++, e.consume(t), t === 92 ? d : u;
	}
	function d(t) {
		return t === 91 || t === 92 || t === 93 ? (e.consume(t), o++, u) : u(t);
	}
	function f(t) {
		return t === 58 ? (e.enter("definitionMarker"), e.consume(t), e.exit("definitionMarker"), i.includes(a) || i.push(a), G(e, p, "gfmFootnoteDefinitionWhitespace")) : n(t);
	}
	function p(e) {
		return t(e);
	}
}
function fm(e, t, n) {
	return e.check(hs, t, e.attempt(om, t, n));
}
function pm(e) {
	e.exit("gfmFootnoteDefinition");
}
function mm(e, t, n) {
	let r = this;
	return G(e, i, "gfmFootnoteDefinitionIndent", 5);
	function i(e) {
		let i = r.events[r.events.length - 1];
		return i && i[1].type === "gfmFootnoteDefinitionIndent" && i[2].sliceSerialize(i[1], !0).length === 4 ? t(e) : n(e);
	}
}
//#endregion
//#region node_modules/micromark-extension-gfm-strikethrough/lib/syntax.js
function hm(e) {
	let t = (e || {}).singleTilde, n = {
		name: "strikethrough",
		tokenize: i,
		resolveAll: r
	};
	return t ??= !0, {
		text: { 126: n },
		insideSpan: { null: [n] },
		attentionMarkers: { null: [126] }
	};
	function r(e, t) {
		let n = -1;
		for (; ++n < e.length;) if (e[n][0] === "enter" && e[n][1].type === "strikethroughSequenceTemporary" && e[n][1]._close) {
			let r = n;
			for (; r--;) if (e[r][0] === "exit" && e[r][1].type === "strikethroughSequenceTemporary" && e[r][1]._open && e[n][1].end.offset - e[n][1].start.offset === e[r][1].end.offset - e[r][1].start.offset) {
				e[n][1].type = "strikethroughSequence", e[r][1].type = "strikethroughSequence";
				let i = {
					type: "strikethrough",
					start: Object.assign({}, e[r][1].start),
					end: Object.assign({}, e[n][1].end)
				}, a = {
					type: "strikethroughText",
					start: Object.assign({}, e[r][1].end),
					end: Object.assign({}, e[n][1].start)
				}, o = [
					[
						"enter",
						i,
						t
					],
					[
						"enter",
						e[r][1],
						t
					],
					[
						"exit",
						e[r][1],
						t
					],
					[
						"enter",
						a,
						t
					]
				], s = t.parser.constructs.insideSpan.null;
				s && Fo(o, o.length, 0, cs(s, e.slice(r + 1, n), t)), Fo(o, o.length, 0, [
					[
						"exit",
						a,
						t
					],
					[
						"enter",
						e[n][1],
						t
					],
					[
						"exit",
						e[n][1],
						t
					],
					[
						"exit",
						i,
						t
					]
				]), Fo(e, r - 1, n - r + 3, o), n = r + o.length - 2;
				break;
			}
		}
		for (n = -1; ++n < e.length;) e[n][1].type === "strikethroughSequenceTemporary" && (e[n][1].type = "data");
		return e;
	}
	function i(e, n, r) {
		let i = this.previous, a = this.events, o = 0;
		return s;
		function s(t) {
			return i === 126 && a[a.length - 1][1].type !== "characterEscape" ? r(t) : (e.enter("strikethroughSequenceTemporary"), c(t));
		}
		function c(a) {
			let s = ss(i);
			if (a === 126) return o > 1 ? r(a) : (e.consume(a), o++, c);
			if (o < 2 && !t) return r(a);
			let l = e.exit("strikethroughSequenceTemporary"), u = ss(a);
			return l._open = !u || u === 2 && !!s, l._close = !s || s === 2 && !!u, n(a);
		}
	}
}
//#endregion
//#region node_modules/micromark-extension-gfm-table/lib/edit-map.js
var gm = class {
	constructor() {
		this.map = [];
	}
	add(e, t, n) {
		_m(this, e, t, n);
	}
	consume(e) {
		/* c8 ignore next 3 -- `resolve` is never called without tables, so without edits. */
		if (this.map.sort(function(e, t) {
			return e[0] - t[0];
		}), this.map.length === 0) return;
		let t = this.map.length, n = [];
		for (; t > 0;) --t, n.push(e.slice(this.map[t][0] + this.map[t][1]), this.map[t][2]), e.length = this.map[t][0];
		n.push(e.slice()), e.length = 0;
		let r = n.pop();
		for (; r;) {
			for (let t of r) e.push(t);
			r = n.pop();
		}
		this.map.length = 0;
	}
};
function _m(e, t, n, r) {
	let i = 0;
	if (!(n === 0 && r.length === 0)) {
		for (; i < e.map.length;) {
			if (e.map[i][0] === t) {
				e.map[i][1] += n, e.map[i][2].push(...r);
				return;
			}
			i += 1;
		}
		e.map.push([
			t,
			n,
			r
		]);
	}
}
//#endregion
//#region node_modules/micromark-extension-gfm-table/lib/infer.js
function vm(e, t) {
	let n = !1, r = [];
	for (; t < e.length;) {
		let i = e[t];
		if (n) {
			if (i[0] === "enter") i[1].type === "tableContent" && r.push(e[t + 1][1].type === "tableDelimiterMarker" ? "left" : "none");
			else if (i[1].type === "tableContent") {
				if (e[t - 1][1].type === "tableDelimiterMarker") {
					let e = r.length - 1;
					r[e] = r[e] === "left" ? "center" : "right";
				}
			} else if (i[1].type === "tableDelimiterRow") break;
		} else i[0] === "enter" && i[1].type === "tableDelimiterRow" && (n = !0);
		t += 1;
	}
	return r;
}
//#endregion
//#region node_modules/micromark-extension-gfm-table/lib/syntax.js
function ym() {
	return { flow: { null: {
		name: "table",
		tokenize: bm,
		resolveAll: xm
	} } };
}
function bm(e, t, n) {
	let r = this, i = 0, a = 0, o;
	return s;
	function s(e) {
		let t = r.events.length - 1;
		for (; t > -1;) {
			let e = r.events[t][1].type;
			if (e === "lineEnding" || e === "linePrefix") t--;
			else break;
		}
		let i = t > -1 ? r.events[t][1].type : null, a = i === "tableHead" || i === "tableRow" ? S : c;
		return a === S && r.parser.lazy[r.now().line] ? n(e) : a(e);
	}
	function c(t) {
		return e.enter("tableHead"), e.enter("tableRow"), l(t);
	}
	function l(e) {
		return e === 124 ? u(e) : (o = !0, a += 1, u(e));
	}
	function u(t) {
		return t === null ? n(t) : U(t) ? a > 1 ? (a = 0, r.interrupt = !0, e.exit("tableRow"), e.enter("lineEnding"), e.consume(t), e.exit("lineEnding"), p) : n(t) : W(t) ? G(e, u, "whitespace")(t) : (a += 1, o && (o = !1, i += 1), t === 124 ? (e.enter("tableCellDivider"), e.consume(t), e.exit("tableCellDivider"), o = !0, u) : (e.enter("data"), d(t)));
	}
	function d(t) {
		return t === null || t === 124 || Xo(t) ? (e.exit("data"), u(t)) : (e.consume(t), t === 92 ? f : d);
	}
	function f(t) {
		return t === 92 || t === 124 ? (e.consume(t), d) : d(t);
	}
	function p(t) {
		return r.interrupt = !1, r.parser.lazy[r.now().line] ? n(t) : (e.enter("tableDelimiterRow"), o = !1, W(t) ? G(e, m, "linePrefix", r.parser.constructs.disable.null.includes("codeIndented") ? void 0 : 4)(t) : m(t));
	}
	function m(t) {
		return t === 45 || t === 58 ? g(t) : t === 124 ? (o = !0, e.enter("tableCellDivider"), e.consume(t), e.exit("tableCellDivider"), h) : x(t);
	}
	function h(t) {
		return W(t) ? G(e, g, "whitespace")(t) : g(t);
	}
	function g(t) {
		return t === 58 ? (a += 1, o = !0, e.enter("tableDelimiterMarker"), e.consume(t), e.exit("tableDelimiterMarker"), _) : t === 45 ? (a += 1, _(t)) : t === null || U(t) ? b(t) : x(t);
	}
	function _(t) {
		return t === 45 ? (e.enter("tableDelimiterFiller"), v(t)) : x(t);
	}
	function v(t) {
		return t === 45 ? (e.consume(t), v) : t === 58 ? (o = !0, e.exit("tableDelimiterFiller"), e.enter("tableDelimiterMarker"), e.consume(t), e.exit("tableDelimiterMarker"), y) : (e.exit("tableDelimiterFiller"), y(t));
	}
	function y(t) {
		return W(t) ? G(e, b, "whitespace")(t) : b(t);
	}
	function b(n) {
		return n === 124 ? m(n) : n === null || U(n) ? !o || i !== a ? x(n) : (e.exit("tableDelimiterRow"), e.exit("tableHead"), t(n)) : x(n);
	}
	function x(e) {
		return n(e);
	}
	function S(t) {
		return e.enter("tableRow"), C(t);
	}
	function C(n) {
		return n === 124 ? (e.enter("tableCellDivider"), e.consume(n), e.exit("tableCellDivider"), C) : n === null || U(n) ? (e.exit("tableRow"), t(n)) : W(n) ? G(e, C, "whitespace")(n) : (e.enter("data"), w(n));
	}
	function w(t) {
		return t === null || t === 124 || Xo(t) ? (e.exit("data"), C(t)) : (e.consume(t), t === 92 ? T : w);
	}
	function T(t) {
		return t === 92 || t === 124 ? (e.consume(t), w) : w(t);
	}
}
function xm(e, t) {
	let n = -1, r = !0, i = 0, a = [
		0,
		0,
		0,
		0
	], o = [
		0,
		0,
		0,
		0
	], s = !1, c = 0, l, u, d, f = new gm();
	for (; ++n < e.length;) {
		let p = e[n], m = p[1];
		p[0] === "enter" ? m.type === "tableHead" ? (s = !1, c !== 0 && (Cm(f, t, c, l, u), u = void 0, c = 0), l = {
			type: "table",
			start: Object.assign({}, m.start),
			end: Object.assign({}, m.end)
		}, f.add(n, 0, [[
			"enter",
			l,
			t
		]])) : m.type === "tableRow" || m.type === "tableDelimiterRow" ? (r = !0, d = void 0, a = [
			0,
			0,
			0,
			0
		], o = [
			0,
			n + 1,
			0,
			0
		], s && (s = !1, u = {
			type: "tableBody",
			start: Object.assign({}, m.start),
			end: Object.assign({}, m.end)
		}, f.add(n, 0, [[
			"enter",
			u,
			t
		]])), i = m.type === "tableDelimiterRow" ? 2 : u ? 3 : 1) : i && (m.type === "data" || m.type === "tableDelimiterMarker" || m.type === "tableDelimiterFiller") ? (r = !1, o[2] === 0 && (a[1] !== 0 && (o[0] = o[1], d = Sm(f, t, a, i, void 0, d), a = [
			0,
			0,
			0,
			0
		]), o[2] = n)) : m.type === "tableCellDivider" && (r ? r = !1 : (a[1] !== 0 && (o[0] = o[1], d = Sm(f, t, a, i, void 0, d)), a = o, o = [
			a[1],
			n,
			0,
			0
		])) : m.type === "tableHead" ? (s = !0, c = n) : m.type === "tableRow" || m.type === "tableDelimiterRow" ? (c = n, a[1] === 0 ? o[1] !== 0 && (d = Sm(f, t, o, i, n, d)) : (o[0] = o[1], d = Sm(f, t, a, i, n, d)), i = 0) : i && (m.type === "data" || m.type === "tableDelimiterMarker" || m.type === "tableDelimiterFiller") && (o[3] = n);
	}
	for (c !== 0 && Cm(f, t, c, l, u), f.consume(t.events), n = -1; ++n < t.events.length;) {
		let e = t.events[n];
		e[0] === "enter" && e[1].type === "table" && (e[1]._align = vm(t.events, n));
	}
	return e;
}
function Sm(e, t, n, r, i, a) {
	let o = r === 1 ? "tableHeader" : r === 2 ? "tableDelimiter" : "tableData";
	n[0] !== 0 && (a.end = Object.assign({}, wm(t.events, n[0])), e.add(n[0], 0, [[
		"exit",
		a,
		t
	]]));
	let s = wm(t.events, n[1]);
	if (a = {
		type: o,
		start: Object.assign({}, s),
		end: Object.assign({}, s)
	}, e.add(n[1], 0, [[
		"enter",
		a,
		t
	]]), n[2] !== 0) {
		let i = wm(t.events, n[2]), a = wm(t.events, n[3]), o = {
			type: "tableContent",
			start: Object.assign({}, i),
			end: Object.assign({}, a)
		};
		if (e.add(n[2], 0, [[
			"enter",
			o,
			t
		]]), r !== 2) {
			let r = t.events[n[2]], i = t.events[n[3]];
			if (r[1].end = Object.assign({}, i[1].end), r[1].type = "chunkText", r[1].contentType = "text", n[3] > n[2] + 1) {
				let t = n[2] + 1, r = n[3] - n[2] - 1;
				e.add(t, r, []);
			}
		}
		e.add(n[3] + 1, 0, [[
			"exit",
			o,
			t
		]]);
	}
	return i !== void 0 && (a.end = Object.assign({}, wm(t.events, i)), e.add(i, 0, [[
		"exit",
		a,
		t
	]]), a = void 0), a;
}
function Cm(e, t, n, r, i) {
	let a = [], o = wm(t.events, n);
	i && (i.end = Object.assign({}, o), a.push([
		"exit",
		i,
		t
	])), r.end = Object.assign({}, o), a.push([
		"exit",
		r,
		t
	]), e.add(n + 1, 0, a);
}
function wm(e, t) {
	let n = e[t], r = n[0] === "enter" ? "start" : "end";
	return n[1][r];
}
//#endregion
//#region node_modules/micromark-extension-gfm-task-list-item/lib/syntax.js
var Tm = {
	name: "tasklistCheck",
	tokenize: Dm
};
function Em() {
	return { text: { 91: Tm } };
}
function Dm(e, t, n) {
	let r = this;
	return i;
	function i(t) {
		return r.previous !== null || !r._gfmTasklistFirstContentOfListItem ? n(t) : (e.enter("taskListCheck"), e.enter("taskListCheckMarker"), e.consume(t), e.exit("taskListCheckMarker"), a);
	}
	function a(t) {
		return Xo(t) ? (e.enter("taskListCheckValueUnchecked"), e.consume(t), e.exit("taskListCheckValueUnchecked"), o) : t === 88 || t === 120 ? (e.enter("taskListCheckValueChecked"), e.consume(t), e.exit("taskListCheckValueChecked"), o) : n(t);
	}
	function o(t) {
		return t === 93 ? (e.enter("taskListCheckMarker"), e.consume(t), e.exit("taskListCheckMarker"), e.exit("taskListCheck"), s) : n(t);
	}
	function s(r) {
		return U(r) ? t(r) : W(r) ? e.check({ tokenize: Om }, t, n)(r) : n(r);
	}
}
function Om(e, t, n) {
	return G(e, r, "whitespace");
	function r(e) {
		return e === null ? n(e) : t(e);
	}
}
//#endregion
//#region node_modules/micromark-extension-gfm/index.js
function km(e) {
	return Ro([
		Gp(),
		sm(),
		hm(e),
		ym(),
		Em()
	]);
}
//#endregion
//#region node_modules/remark-gfm/lib/index.js
var Am = {};
function jm(e) {
	let t = this, n = e || Am, r = t.data(), i = r.micromarkExtensions ||= [], a = r.fromMarkdownExtensions ||= [], o = r.toMarkdownExtensions ||= [];
	i.push(km(n)), a.push(Pp()), o.push(Fp(n));
}
//#endregion
//#region node_modules/turndown/lib/turndown.browser.es.js
function Mm(e) {
	for (var t = 1; t < arguments.length; t++) {
		var n = arguments[t];
		for (var r in n) Object.prototype.hasOwnProperty.call(n, r) && (e[r] = n[r]);
	}
	return e;
}
function Nm(e, t) {
	return Array(t + 1).join(e);
}
function Pm(e) {
	return e.replace(/^\n*/, "");
}
function Fm(e) {
	for (var t = e.length; t > 0 && e[t - 1] === "\n";) t--;
	return e.substring(0, t);
}
function Im(e) {
	return Fm(Pm(e));
}
var Lm = /* @__PURE__ */ "ADDRESS.ARTICLE.ASIDE.AUDIO.BLOCKQUOTE.BODY.CANVAS.CENTER.DD.DIR.DIV.DL.DT.FIELDSET.FIGCAPTION.FIGURE.FOOTER.FORM.FRAMESET.H1.H2.H3.H4.H5.H6.HEADER.HGROUP.HR.HTML.ISINDEX.LI.MAIN.MENU.NAV.NOFRAMES.NOSCRIPT.OL.OUTPUT.P.PRE.SECTION.TABLE.TBODY.TD.TFOOT.TH.THEAD.TR.UL".split(".");
function Rm(e) {
	return Gm(e, Lm);
}
var zm = [
	"AREA",
	"BASE",
	"BR",
	"COL",
	"COMMAND",
	"EMBED",
	"HR",
	"IMG",
	"INPUT",
	"KEYGEN",
	"LINK",
	"META",
	"PARAM",
	"SOURCE",
	"TRACK",
	"WBR"
];
function Bm(e) {
	return Gm(e, zm);
}
function Vm(e) {
	return Km(e, zm);
}
var Hm = [
	"A",
	"TABLE",
	"THEAD",
	"TBODY",
	"TFOOT",
	"TH",
	"TD",
	"IFRAME",
	"SCRIPT",
	"AUDIO",
	"VIDEO"
];
function Um(e) {
	return Gm(e, Hm);
}
function Wm(e) {
	return Km(e, Hm);
}
function Gm(e, t) {
	return t.indexOf(e.nodeName) >= 0;
}
function Km(e, t) {
	return e.getElementsByTagName && t.some(function(t) {
		return e.getElementsByTagName(t).length;
	});
}
var qm = [
	[/\\/g, "\\\\"],
	[/\*/g, "\\*"],
	[/^-/g, "\\-"],
	[/^\+ /g, "\\+ "],
	[/^(=+)/g, "\\$1"],
	[/^(#{1,6}) /g, "\\$1 "],
	[/`/g, "\\`"],
	[/^~~~/g, "\\~~~"],
	[/\[/g, "\\["],
	[/\]/g, "\\]"],
	[/^>/g, "\\>"],
	[/_/g, "\\_"],
	[/^(\d+)\. /g, "$1\\. "]
];
function Jm(e) {
	return qm.reduce(function(e, t) {
		return e.replace(t[0], t[1]);
	}, e);
}
var Ym = {};
Ym.paragraph = {
	filter: "p",
	replacement: function(e) {
		return "\n\n" + e + "\n\n";
	}
}, Ym.lineBreak = {
	filter: "br",
	replacement: function(e, t, n) {
		return n.br + "\n";
	}
}, Ym.heading = {
	filter: [
		"h1",
		"h2",
		"h3",
		"h4",
		"h5",
		"h6"
	],
	replacement: function(e, t, n) {
		var r = Number(t.nodeName.charAt(1));
		if (n.headingStyle === "setext" && r < 3) {
			var i = Nm(r === 1 ? "=" : "-", e.length);
			return "\n\n" + e + "\n" + i + "\n\n";
		} else return "\n\n" + Nm("#", r) + " " + e + "\n\n";
	}
}, Ym.blockquote = {
	filter: "blockquote",
	replacement: function(e) {
		return e = Im(e).replace(/^/gm, "> "), "\n\n" + e + "\n\n";
	}
}, Ym.list = {
	filter: ["ul", "ol"],
	replacement: function(e, t) {
		var n = t.parentNode;
		return n.nodeName === "LI" && n.lastElementChild === t ? "\n" + e : "\n\n" + e + "\n\n";
	}
}, Ym.listItem = {
	filter: "li",
	replacement: function(e, t, n) {
		var r = n.bulletListMarker + "   ", i = t.parentNode;
		if (i.nodeName === "OL") {
			var a = i.getAttribute("start"), o = Array.prototype.indexOf.call(i.children, t);
			r = (a ? Number(a) + o : o + 1) + ".  ";
		}
		var s = /\n$/.test(e);
		return e = Im(e) + (s ? "\n" : ""), e = e.replace(/\n/gm, "\n" + " ".repeat(r.length)), r + e + (t.nextSibling ? "\n" : "");
	}
}, Ym.indentedCodeBlock = {
	filter: function(e, t) {
		return t.codeBlockStyle === "indented" && e.nodeName === "PRE" && e.firstChild && e.firstChild.nodeName === "CODE";
	},
	replacement: function(e, t, n) {
		return "\n\n    " + t.firstChild.textContent.replace(/\n/g, "\n    ") + "\n\n";
	}
}, Ym.fencedCodeBlock = {
	filter: function(e, t) {
		return t.codeBlockStyle === "fenced" && e.nodeName === "PRE" && e.firstChild && e.firstChild.nodeName === "CODE";
	},
	replacement: function(e, t, n) {
		for (var r = ((t.firstChild.getAttribute("class") || "").match(/language-(\S+)/) || [null, ""])[1], i = t.firstChild.textContent, a = n.fence.charAt(0), o = 3, s = RegExp("^" + a + "{3,}", "gm"), c; c = s.exec(i);) c[0].length >= o && (o = c[0].length + 1);
		var l = Nm(a, o);
		return "\n\n" + l + r + "\n" + i.replace(/\n$/, "") + "\n" + l + "\n\n";
	}
}, Ym.horizontalRule = {
	filter: "hr",
	replacement: function(e, t, n) {
		return "\n\n" + n.hr + "\n\n";
	}
}, Ym.inlineLink = {
	filter: function(e, t) {
		return t.linkStyle === "inlined" && e.nodeName === "A" && e.getAttribute("href");
	},
	replacement: function(e, t) {
		var n = Zm(t.getAttribute("href")), r = Qm(Xm(t.getAttribute("title"))), i = r ? " \"" + r + "\"" : "";
		return "[" + e + "](" + n + i + ")";
	}
}, Ym.referenceLink = {
	filter: function(e, t) {
		return t.linkStyle === "referenced" && e.nodeName === "A" && e.getAttribute("href");
	},
	replacement: function(e, t, n) {
		var r = Zm(t.getAttribute("href")), i = Xm(t.getAttribute("title"));
		i &&= " \"" + Qm(i) + "\"";
		var a, o;
		switch (n.linkReferenceStyle) {
			case "collapsed":
				a = "[" + e + "][]", o = "[" + e + "]: " + r + i;
				break;
			case "shortcut":
				a = "[" + e + "]", o = "[" + e + "]: " + r + i;
				break;
			default:
				var s = this.references.length + 1;
				a = "[" + e + "][" + s + "]", o = "[" + s + "]: " + r + i;
		}
		return this.references.push(o), a;
	},
	references: [],
	append: function(e) {
		var t = "";
		return this.references.length && (t = "\n\n" + this.references.join("\n") + "\n\n", this.references = []), t;
	}
}, Ym.emphasis = {
	filter: ["em", "i"],
	replacement: function(e, t, n) {
		return e.trim() ? n.emDelimiter + e + n.emDelimiter : "";
	}
}, Ym.strong = {
	filter: ["strong", "b"],
	replacement: function(e, t, n) {
		return e.trim() ? n.strongDelimiter + e + n.strongDelimiter : "";
	}
}, Ym.code = {
	filter: function(e) {
		var t = e.previousSibling || e.nextSibling, n = e.parentNode.nodeName === "PRE" && !t;
		return e.nodeName === "CODE" && !n;
	},
	replacement: function(e) {
		if (!e) return "";
		e = e.replace(/\r?\n|\r/g, " ");
		for (var t = /^`|^ .*?[^ ].* $|`$/.test(e) ? " " : "", n = "`", r = e.match(/`+/gm) || []; r.indexOf(n) !== -1;) n += "`";
		return n + t + e + t + n;
	}
}, Ym.image = {
	filter: "img",
	replacement: function(e, t) {
		var n = Jm(Xm(t.getAttribute("alt"))), r = Zm(t.getAttribute("src") || ""), i = Xm(t.getAttribute("title")), a = i ? " \"" + Qm(i) + "\"" : "";
		return r ? "![" + n + "](" + r + a + ")" : "";
	}
};
function Xm(e) {
	return e ? e.replace(/(\n+\s*)+/g, "\n") : "";
}
function Zm(e) {
	var t = e.replace(/([<>()])/g, "\\$1");
	return t.indexOf(" ") >= 0 ? "<" + t + ">" : t;
}
function Qm(e) {
	return e.replace(/"/g, "\\\"");
}
function $m(e) {
	for (var t in this.options = e, this._keep = [], this._remove = [], this.blankRule = { replacement: e.blankReplacement }, this.keepReplacement = e.keepReplacement, this.defaultRule = { replacement: e.defaultReplacement }, this.array = [], e.rules) this.array.push(e.rules[t]);
}
$m.prototype = {
	add: function(e, t) {
		this.array.unshift(t);
	},
	keep: function(e) {
		this._keep.unshift({
			filter: e,
			replacement: this.keepReplacement
		});
	},
	remove: function(e) {
		this._remove.unshift({
			filter: e,
			replacement: function() {
				return "";
			}
		});
	},
	forNode: function(e) {
		if (e.isBlank) return this.blankRule;
		var t;
		return (t = eh(this.array, e, this.options)) || (t = eh(this._keep, e, this.options)) || (t = eh(this._remove, e, this.options)) ? t : this.defaultRule;
	},
	forEach: function(e) {
		for (var t = 0; t < this.array.length; t++) e(this.array[t], t);
	}
};
function eh(e, t, n) {
	for (var r = 0; r < e.length; r++) {
		var i = e[r];
		if (th(i, t, n)) return i;
	}
}
function th(e, t, n) {
	var r = e.filter;
	if (typeof r == "string") {
		if (r === t.nodeName.toLowerCase()) return !0;
	} else if (Array.isArray(r)) {
		if (r.indexOf(t.nodeName.toLowerCase()) > -1) return !0;
	} else if (typeof r == "function") {
		if (r.call(e, t, n)) return !0;
	} else throw TypeError("`filter` needs to be a string, array, or function");
}
function nh(e) {
	var t = e.element, n = e.isBlock, r = e.isVoid, i = e.isPre || function(e) {
		return e.nodeName === "PRE";
	};
	if (!(!t.firstChild || i(t))) {
		for (var a = null, o = !1, s = null, c = ih(s, t, i); c !== t;) {
			if (c.nodeType === 3 || c.nodeType === 4) {
				var l = c.data.replace(/[ \r\n\t]+/g, " ");
				if ((!a || / $/.test(a.data)) && !o && l[0] === " " && (l = l.substr(1)), !l) {
					c = rh(c);
					continue;
				}
				c.data = l, a = c;
			} else if (c.nodeType === 1) n(c) || c.nodeName === "BR" ? (a && (a.data = a.data.replace(/ $/, "")), a = null, o = !1) : r(c) || i(c) ? (a = null, o = !0) : a && (o = !1);
			else {
				c = rh(c);
				continue;
			}
			var u = ih(s, c, i);
			s = c, c = u;
		}
		a && (a.data = a.data.replace(/ $/, ""), a.data || rh(a));
	}
}
function rh(e) {
	var t = e.nextSibling || e.parentNode;
	return e.parentNode.removeChild(e), t;
}
function ih(e, t, n) {
	return e && e.parentNode === t || n(t) ? t.nextSibling || t.parentNode : t.firstChild || t.nextSibling || t.parentNode;
}
var ah = typeof window < "u" ? window : {};
function oh() {
	var e = ah.DOMParser, t = !1;
	try {
		new e().parseFromString("", "text/html") && (t = !0);
	} catch {}
	return t;
}
function sh() {
	var e = function() {};
	return ch() ? e.prototype.parseFromString = function(e) {
		var t = new window.ActiveXObject("htmlfile");
		return t.designMode = "on", t.open(), t.write(e), t.close(), t;
	} : e.prototype.parseFromString = function(e) {
		var t = document.implementation.createHTMLDocument("");
		return t.open(), t.write(e), t.close(), t;
	}, e;
}
function ch() {
	var e = !1;
	try {
		document.implementation.createHTMLDocument("").open();
	} catch {
		ah.ActiveXObject && (e = !0);
	}
	return e;
}
var lh = oh() ? ah.DOMParser : sh();
function uh(e, t) {
	var n = typeof e == "string" ? fh().parseFromString("<x-turndown id=\"turndown-root\">" + e + "</x-turndown>", "text/html").getElementById("turndown-root") : e.cloneNode(!0);
	return nh({
		element: n,
		isBlock: Rm,
		isVoid: Bm,
		isPre: t.preformattedCode ? ph : null
	}), n;
}
var dh;
function fh() {
	return dh ||= new lh(), dh;
}
function ph(e) {
	return e.nodeName === "PRE" || e.nodeName === "CODE";
}
function mh(e, t) {
	return e.isBlock = Rm(e), e.isCode = e.nodeName === "CODE" || e.parentNode.isCode, e.isBlank = hh(e), e.flankingWhitespace = gh(e, t), e;
}
function hh(e) {
	return !Bm(e) && !Um(e) && /^\s*$/i.test(e.textContent) && !Vm(e) && !Wm(e);
}
function gh(e, t) {
	if (e.isBlock || t.preformattedCode && e.isCode) return {
		leading: "",
		trailing: ""
	};
	var n = _h(e.textContent);
	return n.leadingAscii && vh("left", e, t) && (n.leading = n.leadingNonAscii), n.trailingAscii && vh("right", e, t) && (n.trailing = n.trailingNonAscii), {
		leading: n.leading,
		trailing: n.trailing
	};
}
function _h(e) {
	var t = e.match(/^(([ \t\r\n]*)(\s*))(?:(?=\S)[\s\S]*\S)?((\s*?)([ \t\r\n]*))$/);
	return {
		leading: t[1],
		leadingAscii: t[2],
		leadingNonAscii: t[3],
		trailing: t[4],
		trailingNonAscii: t[5],
		trailingAscii: t[6]
	};
}
function vh(e, t, n) {
	var r, i, a;
	return e === "left" ? (r = t.previousSibling, i = / $/) : (r = t.nextSibling, i = /^ /), r && (r.nodeType === 3 ? a = i.test(r.nodeValue) : n.preformattedCode && r.nodeName === "CODE" ? a = !1 : r.nodeType === 1 && !Rm(r) && (a = i.test(r.textContent))), a;
}
var yh = Array.prototype.reduce;
function bh(e) {
	if (!(this instanceof bh)) return new bh(e);
	var t = {
		rules: Ym,
		headingStyle: "setext",
		hr: "* * *",
		bulletListMarker: "*",
		codeBlockStyle: "indented",
		fence: "```",
		emDelimiter: "_",
		strongDelimiter: "**",
		linkStyle: "inlined",
		linkReferenceStyle: "full",
		br: "  ",
		preformattedCode: !1,
		blankReplacement: function(e, t) {
			return t.isBlock ? "\n\n" : "";
		},
		keepReplacement: function(e, t) {
			return t.isBlock ? "\n\n" + t.outerHTML + "\n\n" : t.outerHTML;
		},
		defaultReplacement: function(e, t) {
			return t.isBlock ? "\n\n" + e + "\n\n" : e;
		}
	};
	this.options = Mm({}, t, e), this.rules = new $m(this.options);
}
bh.prototype = {
	turndown: function(e) {
		if (!Th(e)) throw TypeError(e + " is not a string, or an element/document/fragment node.");
		if (e === "") return "";
		var t = xh.call(this, new uh(e, this.options));
		return Sh.call(this, t);
	},
	use: function(e) {
		if (Array.isArray(e)) for (var t = 0; t < e.length; t++) this.use(e[t]);
		else if (typeof e == "function") e(this);
		else throw TypeError("plugin must be a Function or an Array of Functions");
		return this;
	},
	addRule: function(e, t) {
		return this.rules.add(e, t), this;
	},
	keep: function(e) {
		return this.rules.keep(e), this;
	},
	remove: function(e) {
		return this.rules.remove(e), this;
	},
	escape: function(e) {
		return Jm(e);
	}
};
function xh(e) {
	var t = this;
	return yh.call(e.childNodes, function(e, n) {
		n = new mh(n, t.options);
		var r = "";
		return n.nodeType === 3 ? r = n.isCode ? n.nodeValue : t.escape(n.nodeValue) : n.nodeType === 1 && (r = Ch.call(t, n)), wh(e, r);
	}, "");
}
function Sh(e) {
	var t = this;
	return this.rules.forEach(function(n) {
		typeof n.append == "function" && (e = wh(e, n.append(t.options)));
	}), e.replace(/^[\t\r\n]+/, "").replace(/[\t\r\n\s]+$/, "");
}
function Ch(e) {
	var t = this.rules.forNode(e), n = xh.call(this, e), r = e.flankingWhitespace;
	return (r.leading || r.trailing) && (n = n.trim()), r.leading + t.replacement(n, e, this.options) + r.trailing;
}
function wh(e, t) {
	var n = Fm(e), r = Pm(t), i = Math.max(e.length - n.length, t.length - r.length);
	return n + "\n\n".substring(0, i) + r;
}
function Th(e) {
	return e != null && (typeof e == "string" || e.nodeType && (e.nodeType === 1 || e.nodeType === 9 || e.nodeType === 11));
}
//#endregion
//#region node_modules/lucide-react/dist/esm/shared/src/utils/mergeClasses.mjs
var Eh = (...e) => e.filter((e, t, n) => !!e && e.trim() !== "" && n.indexOf(e) === t).join(" ").trim(), Dh = (e) => e.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase(), Oh = (e) => e.replace(/^([A-Z])|[\s-_]+(\w)/g, (e, t, n) => n ? n.toUpperCase() : t.toLowerCase()), kh = (e) => {
	let t = Oh(e);
	return t.charAt(0).toUpperCase() + t.slice(1);
}, Ah = {
	xmlns: "http://www.w3.org/2000/svg",
	width: 24,
	height: 24,
	viewBox: "0 0 24 24",
	fill: "none",
	stroke: "currentColor",
	strokeWidth: 2,
	strokeLinecap: "round",
	strokeLinejoin: "round"
}, jh = (e) => {
	for (let t in e) if (t.startsWith("aria-") || t === "role" || t === "title") return !0;
	return !1;
}, Mh = (0, I.createContext)({}), Nh = () => (0, I.useContext)(Mh), Ph = (0, I.forwardRef)(({ color: e, size: t, strokeWidth: n, absoluteStrokeWidth: r, className: i = "", children: a, iconNode: o, ...s }, c) => {
	let { size: l = 24, strokeWidth: u = 2, absoluteStrokeWidth: d = !1, color: f = "currentColor", className: p = "" } = Nh() ?? {}, m = r ?? d ? Number(n ?? u) * 24 / Number(t ?? l) : n ?? u;
	return (0, I.createElement)("svg", {
		ref: c,
		...Ah,
		width: t ?? l ?? Ah.width,
		height: t ?? l ?? Ah.height,
		stroke: e ?? f,
		strokeWidth: m,
		className: Eh("lucide", p, i),
		...!a && !jh(s) && { "aria-hidden": "true" },
		...s
	}, [...o.map(([e, t]) => (0, I.createElement)(e, t)), ...Array.isArray(a) ? a : [a]]);
}), X = (e, t) => {
	let n = (0, I.forwardRef)(({ className: n, ...r }, i) => (0, I.createElement)(Ph, {
		ref: i,
		iconNode: t,
		className: Eh(`lucide-${Dh(kh(e))}`, `lucide-${e}`, n),
		...r
	}));
	return n.displayName = kh(e), n;
}, Fh = X("activity", [["path", {
	d: "M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2",
	key: "169zse"
}]]), Ih = X("bold", [["path", {
	d: "M6 12h9a4 4 0 0 1 0 8H7a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h7a4 4 0 0 1 0 8",
	key: "mg9rjx"
}]]), Lh = X("calendar", [
	["path", {
		d: "M8 2v4",
		key: "1cmpym"
	}],
	["path", {
		d: "M16 2v4",
		key: "4m81vk"
	}],
	["rect", {
		width: "18",
		height: "18",
		x: "3",
		y: "4",
		rx: "2",
		key: "1hopcy"
	}],
	["path", {
		d: "M3 10h18",
		key: "8toen8"
	}]
]), Rh = X("chevron-left", [["path", {
	d: "m15 18-6-6 6-6",
	key: "1wnfg3"
}]]), zh = X("chevron-down", [["path", {
	d: "m6 9 6 6 6-6",
	key: "qrunsl"
}]]), Bh = X("chevron-right", [["path", {
	d: "m9 18 6-6-6-6",
	key: "mthhwq"
}]]), Vh = X("circle-alert", [
	["circle", {
		cx: "12",
		cy: "12",
		r: "10",
		key: "1mglay"
	}],
	["line", {
		x1: "12",
		x2: "12",
		y1: "8",
		y2: "12",
		key: "1pkeuh"
	}],
	["line", {
		x1: "12",
		x2: "12.01",
		y1: "16",
		y2: "16",
		key: "4dfq90"
	}]
]), Hh = X("circle-check", [["circle", {
	cx: "12",
	cy: "12",
	r: "10",
	key: "1mglay"
}], ["path", {
	d: "m9 12 2 2 4-4",
	key: "dzmm74"
}]]), Uh = X("circle-dot", [["circle", {
	cx: "12",
	cy: "12",
	r: "10",
	key: "1mglay"
}], ["circle", {
	cx: "12",
	cy: "12",
	r: "1",
	key: "41hilf"
}]]), Wh = X("circle-question-mark", [
	["circle", {
		cx: "12",
		cy: "12",
		r: "10",
		key: "1mglay"
	}],
	["path", {
		d: "M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3",
		key: "1u773s"
	}],
	["path", {
		d: "M12 17h.01",
		key: "p32p05"
	}]
]), Gh = X("code-xml", [
	["path", {
		d: "m18 16 4-4-4-4",
		key: "1inbqp"
	}],
	["path", {
		d: "m6 8-4 4 4 4",
		key: "15zrgr"
	}],
	["path", {
		d: "m14.5 4-5 16",
		key: "e7oirm"
	}]
]), Kh = X("copy", [["rect", {
	width: "14",
	height: "14",
	x: "8",
	y: "8",
	rx: "2",
	ry: "2",
	key: "17jyea"
}], ["path", {
	d: "M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2",
	key: "zix9uf"
}]]), qh = X("external-link", [
	["path", {
		d: "M15 3h6v6",
		key: "1q9fwt"
	}],
	["path", {
		d: "M10 14 21 3",
		key: "gplh6r"
	}],
	["path", {
		d: "M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6",
		key: "a6xqqp"
	}]
]), Jh = X("eye-off", [
	["path", {
		d: "M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49",
		key: "ct8e1f"
	}],
	["path", {
		d: "M14.084 14.158a3 3 0 0 1-4.242-4.242",
		key: "151rxh"
	}],
	["path", {
		d: "M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143",
		key: "13bj9a"
	}],
	["path", {
		d: "m2 2 20 20",
		key: "1ooewy"
	}]
]), Yh = X("eye", [["path", {
	d: "M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0",
	key: "1nclc0"
}], ["circle", {
	cx: "12",
	cy: "12",
	r: "3",
	key: "1v7zrd"
}]]), Xh = X("file-code-corner", [
	["path", {
		d: "M4 12.15V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2h-3.35",
		key: "1wthlu"
	}],
	["path", {
		d: "M14 2v5a1 1 0 0 0 1 1h5",
		key: "wfsgrz"
	}],
	["path", {
		d: "m5 16-3 3 3 3",
		key: "331omg"
	}],
	["path", {
		d: "m9 22 3-3-3-3",
		key: "lsp7cz"
	}]
]), Zh = X("folder-git-2", [
	["path", {
		d: "M18 19a5 5 0 0 1-5-5v8",
		key: "sz5oeg"
	}],
	["path", {
		d: "M9 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v5",
		key: "1w6njk"
	}],
	["circle", {
		cx: "13",
		cy: "12",
		r: "2",
		key: "1j92g6"
	}],
	["circle", {
		cx: "20",
		cy: "19",
		r: "2",
		key: "1obnsp"
	}]
]), Qh = X("git-branch", [
	["path", {
		d: "M15 6a9 9 0 0 0-9 9V3",
		key: "1cii5b"
	}],
	["circle", {
		cx: "18",
		cy: "6",
		r: "3",
		key: "1h7g24"
	}],
	["circle", {
		cx: "6",
		cy: "18",
		r: "3",
		key: "fqmcym"
	}]
]), $h = X("heading-2", [
	["path", {
		d: "M4 12h8",
		key: "17cfdx"
	}],
	["path", {
		d: "M4 18V6",
		key: "1rz3zl"
	}],
	["path", {
		d: "M12 18V6",
		key: "zqpxq5"
	}],
	["path", {
		d: "M21 18h-4c0-4 4-3 4-6 0-1.5-2-2.5-4-1",
		key: "9jr5yi"
	}]
]), eg = X("italic", [
	["line", {
		x1: "19",
		x2: "10",
		y1: "4",
		y2: "4",
		key: "15jd3p"
	}],
	["line", {
		x1: "14",
		x2: "5",
		y1: "20",
		y2: "20",
		key: "bu0au3"
	}],
	["line", {
		x1: "15",
		x2: "9",
		y1: "4",
		y2: "20",
		key: "uljnxc"
	}]
]), tg = X("layout-dashboard", [
	["rect", {
		width: "7",
		height: "9",
		x: "3",
		y: "3",
		rx: "1",
		key: "10lvy0"
	}],
	["rect", {
		width: "7",
		height: "5",
		x: "14",
		y: "3",
		rx: "1",
		key: "16une8"
	}],
	["rect", {
		width: "7",
		height: "9",
		x: "14",
		y: "12",
		rx: "1",
		key: "1hutg5"
	}],
	["rect", {
		width: "7",
		height: "5",
		x: "3",
		y: "16",
		rx: "1",
		key: "ldoo1y"
	}]
]), ng = X("link-2", [
	["path", {
		d: "M9 17H7A5 5 0 0 1 7 7h2",
		key: "8i5ue5"
	}],
	["path", {
		d: "M15 7h2a5 5 0 1 1 0 10h-2",
		key: "1b9ql8"
	}],
	["line", {
		x1: "8",
		x2: "16",
		y1: "12",
		y2: "12",
		key: "1jonct"
	}]
]), rg = X("list-filter", [
	["path", {
		d: "M2 5h20",
		key: "1fs1ex"
	}],
	["path", {
		d: "M6 12h12",
		key: "8npq4p"
	}],
	["path", {
		d: "M9 19h6",
		key: "456am0"
	}]
]), ig = X("list", [
	["path", {
		d: "M3 5h.01",
		key: "18ugdj"
	}],
	["path", {
		d: "M3 12h.01",
		key: "nlz23k"
	}],
	["path", {
		d: "M3 19h.01",
		key: "noohij"
	}],
	["path", {
		d: "M8 5h13",
		key: "1pao27"
	}],
	["path", {
		d: "M8 12h13",
		key: "1za7za"
	}],
	["path", {
		d: "M8 19h13",
		key: "m83p4d"
	}]
]), ag = X("loader-circle", [["path", {
	d: "M21 12a9 9 0 1 1-6.219-8.56",
	key: "13zald"
}]]), og = X("maximize-2", [
	["path", {
		d: "M15 3h6v6",
		key: "1q9fwt"
	}],
	["path", {
		d: "m21 3-7 7",
		key: "1l2asr"
	}],
	["path", {
		d: "m3 21 7-7",
		key: "tjx5ai"
	}],
	["path", {
		d: "M9 21H3v-6",
		key: "wtvkvv"
	}]
]), sg = X("minimize-2", [
	["path", {
		d: "m14 10 7-7",
		key: "oa77jy"
	}],
	["path", {
		d: "M20 10h-6V4",
		key: "mjg0md"
	}],
	["path", {
		d: "m3 21 7-7",
		key: "tjx5ai"
	}],
	["path", {
		d: "M4 14h6v6",
		key: "rmj7iw"
	}]
]), cg = X("play", [["path", {
	d: "M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z",
	key: "10ikf1"
}]]), lg = X("rotate-ccw", [["path", {
	d: "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8",
	key: "1357e3"
}], ["path", {
	d: "M3 3v5h5",
	key: "1xhq8a"
}]]), ug = X("save", [
	["path", {
		d: "M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z",
		key: "1c8476"
	}],
	["path", {
		d: "M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7",
		key: "1ydtos"
	}],
	["path", {
		d: "M7 3v4a1 1 0 0 0 1 1h7",
		key: "t51u73"
	}]
]), dg = X("scan-search", [
	["path", {
		d: "M3 7V5a2 2 0 0 1 2-2h2",
		key: "aa7l1z"
	}],
	["path", {
		d: "M17 3h2a2 2 0 0 1 2 2v2",
		key: "4qcy5o"
	}],
	["path", {
		d: "M21 17v2a2 2 0 0 1-2 2h-2",
		key: "6vwrx8"
	}],
	["path", {
		d: "M7 21H5a2 2 0 0 1-2-2v-2",
		key: "ioqczr"
	}],
	["circle", {
		cx: "12",
		cy: "12",
		r: "3",
		key: "1v7zrd"
	}],
	["path", {
		d: "m16 16-1.9-1.9",
		key: "1dq9hf"
	}]
]), fg = X("search", [["path", {
	d: "m21 21-4.34-4.34",
	key: "14j7rj"
}], ["circle", {
	cx: "11",
	cy: "11",
	r: "8",
	key: "4ej97u"
}]]), pg = X("settings-2", [
	["path", {
		d: "M14 17H5",
		key: "gfn3mx"
	}],
	["path", {
		d: "M19 7h-9",
		key: "6i9tg"
	}],
	["circle", {
		cx: "17",
		cy: "17",
		r: "3",
		key: "18b49y"
	}],
	["circle", {
		cx: "7",
		cy: "7",
		r: "3",
		key: "dfmy0x"
	}]
]), mg = X("shield-check", [["path", {
	d: "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z",
	key: "oel41y"
}], ["path", {
	d: "m9 12 2 2 4-4",
	key: "dzmm74"
}]]), hg = X("sparkles", [
	["path", {
		d: "M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z",
		key: "1s2grr"
	}],
	["path", {
		d: "M20 2v4",
		key: "1rf3ol"
	}],
	["path", {
		d: "M22 4h-4",
		key: "gwowj6"
	}],
	["circle", {
		cx: "4",
		cy: "20",
		r: "2",
		key: "6kqj1y"
	}]
]), gg = X("terminal", [["path", {
	d: "M12 19h8",
	key: "baeox8"
}], ["path", {
	d: "m4 17 6-6-6-6",
	key: "1yngyt"
}]]), _g = X("trash-2", [
	["path", {
		d: "M10 11v6",
		key: "nco0om"
	}],
	["path", {
		d: "M14 11v6",
		key: "outv1u"
	}],
	["path", {
		d: "M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6",
		key: "miytrc"
	}],
	["path", {
		d: "M3 6h18",
		key: "d0wm0j"
	}],
	["path", {
		d: "M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2",
		key: "e791ji"
	}]
]), vg = X("truck", [
	["path", {
		d: "M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2",
		key: "wrbu53"
	}],
	["path", {
		d: "M15 18H9",
		key: "1lyqi6"
	}],
	["path", {
		d: "M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14",
		key: "lysw3i"
	}],
	["circle", {
		cx: "17",
		cy: "18",
		r: "2",
		key: "332jqn"
	}],
	["circle", {
		cx: "7",
		cy: "18",
		r: "2",
		key: "19iecd"
	}]
]), yg = X("user", [["path", {
	d: "M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2",
	key: "975kel"
}], ["circle", {
	cx: "12",
	cy: "7",
	r: "4",
	key: "17ys0d"
}]]), bg = X("workflow", [
	["rect", {
		width: "8",
		height: "8",
		x: "3",
		y: "3",
		rx: "2",
		key: "by2w9f"
	}],
	["path", {
		d: "M7 11v4a2 2 0 0 0 2 2h4",
		key: "xkn7yn"
	}],
	["rect", {
		width: "8",
		height: "8",
		x: "13",
		y: "13",
		rx: "2",
		key: "1cgmvn"
	}]
]), xg = X("x", [["path", {
	d: "M18 6 6 18",
	key: "1bl5f8"
}], ["path", {
	d: "m6 6 12 12",
	key: "d8bk6v"
}]]), Sg = X("zoom-in", [
	["circle", {
		cx: "11",
		cy: "11",
		r: "8",
		key: "4ej97u"
	}],
	["line", {
		x1: "21",
		x2: "16.65",
		y1: "21",
		y2: "16.65",
		key: "13gj7c"
	}],
	["line", {
		x1: "11",
		x2: "11",
		y1: "8",
		y2: "14",
		key: "1vmskp"
	}],
	["line", {
		x1: "8",
		x2: "14",
		y1: "11",
		y2: "11",
		key: "durymu"
	}]
]), Cg = X("zoom-out", [
	["circle", {
		cx: "11",
		cy: "11",
		r: "8",
		key: "4ej97u"
	}],
	["line", {
		x1: "21",
		x2: "16.65",
		y1: "21",
		y2: "16.65",
		key: "13gj7c"
	}],
	["line", {
		x1: "8",
		x2: "14",
		y1: "11",
		y2: "11",
		key: "durymu"
	}]
]), wg = "2.7.5";
Yi.initialize({
	startOnLoad: !1,
	securityLevel: "strict",
	theme: "neutral"
}), Jt.setOptions({
	gfm: !0,
	breaks: !1
});
var Tg = /* @__PURE__ */ new Map(), Eg = /* @__PURE__ */ new Map(), Dg = 0, Og = .5, kg = 3, Ag = .25, jg = "lumon-dashboard-locale", Mg = "lumen-dashboard-locale", Ng = [
	{
		value: "en",
		label: "English"
	},
	{
		value: "zh-Hans",
		label: "简体中文"
	},
	{
		value: "zh-Hant",
		label: "繁體中文"
	}
], Pg = {
	en: {
		"language.label": "Language",
		"language.en": "English",
		"language.zhHans": "简体中文",
		"language.zhHant": "繁體中文",
		"nav.overview": "OVERVIEW",
		"nav.activity": "ACTIVITY",
		"nav.scan": "AUTO SCAN",
		"nav.delivery": "AUTO DELIVERY",
		"nav.patch": "AUTO PATCH",
		"nav.observatory": "OBSERVATORY",
		"nav.repositories": "REPOSITORY",
		"nav.prompts": "WORKFLOW",
		"nav.settings": "SETTINGS",
		"context.overview.title": "MANAGER OVERVIEW",
		"context.overview.description": "Agent ownership, workflow health, and the next human decision.",
		"context.activity.title": "AGENT ACTIVITY",
		"context.activity.description": "Conversation records, outcomes, and the evidence behind each Agent turn.",
		"context.scan.title": "AUTO SCAN",
		"context.scan.description": "Review history and manage tracked findings.",
		"context.delivery.title": "AUTO DELIVERY",
		"context.delivery.description": "Story execution, verification, and pull request delivery.",
		"context.patch.title": "AUTO PATCH",
		"context.patch.description": "Jira Task and Bug capture, focused fixes, and safe handoff.",
		"context.observatory.title": "OBSERVATORY",
		"context.observatory.description": "Browse and edit story briefs and technical plans.",
		"context.repositories.title": "REPOSITORY",
		"context.repositories.description": "Local repositories, automation permissions, and delivery verification policy.",
		"context.prompts.title": "WORKFLOW",
		"context.prompts.description": "The prompts, scripts, control points, and recovery paths behind each local automation.",
		"context.settings.title": "SETTINGS",
		"context.settings.description": "Workspace configuration, scheduling, and local integrations.",
		"common.updated": "Updated {{value}}",
		"common.syncing": "Syncing…",
		"common.project": "Project",
		"common.currentProject": "Current project",
		"common.openSettings": "Open Settings",
		"common.manageCapture": "Manage capture",
		"common.loadingWorkspace": "Loading local workspace state…",
		"common.expandNavigation": "Expand navigation",
		"common.collapseNavigation": "Collapse navigation",
		"common.version": "Version {{value}}",
		"common.staticReport": "Static report mode: interactive actions are unavailable.",
		"common.unableLoadState": "Unable to load Dashboard state",
		"common.requestFailed": "Request failed",
		"common.unsavedSettings": "You have unsaved Settings changes. Leave without saving?",
		"common.unsavedObservatory": "You have unsaved Observatory changes. Leave without saving?",
		"common.noData": "No data available.",
		"common.cancel": "Cancel",
		"common.close": "Close",
		"common.later": "Later",
		"common.save": "Save",
		"common.saving": "Saving…",
		"common.confirm": "Confirm",
		"common.continue": "Continue",
		"common.start": "Start",
		"common.stop": "Stop",
		"common.retry": "Retry",
		"common.loading": "Loading…",
		"common.enabled": "Enabled",
		"common.paused": "Paused",
		"common.active": "Active",
		"common.off": "Off",
		"common.all": "All",
		"common.clear": "Clear",
		"common.selected": "{{count}} selected",
		"common.statusesSelected": "{{count}} statuses selected",
		"common.previous": "Previous",
		"common.next": "Next",
		"common.pageOf": "Page {{page}} of {{count}}",
		"common.showing": "{{count}} shown",
		"common.debugDetails": "Debug details",
		"common.originalPrompt": "Original Agent prompt",
		"common.records": "{{count}} records",
		"common.runs": "{{count}} runs",
		"common.recentEvents": "{{count}} recent events",
		"common.yes": "Yes",
		"common.no": "No",
		"common.unknown": "Unknown",
		"common.workspace": "Workspace",
		"common.agent": "Agent",
		"common.clarification": "Clarification",
		"common.manager": "Manager",
		"common.you": "You",
		"common.trace": "Trace",
		"common.viewActivity": "View activity",
		"common.viewLog": "View log",
		"common.viewTrace": "View trace",
		"common.open": "Open",
		"common.inspect": "Inspect",
		"common.noAgentRoles": "No Agent roles available yet.",
		"common.noAgentQuestions": "No unanswered Agent questions.",
		"common.noConversationRecords": "No conversation records match this filter.",
		"common.noFindings": "No findings match this status.",
		"common.noStoriesFilter": "No stories match this filter.",
		"common.noStories": "No stories found in the docs repository.",
		"common.selectStory": "Select a story to inspect.",
		"common.noAgentHistory": "No Agent conversation store is available yet. New Feishu conversations will appear here after the gateway starts.",
		"common.askAgents": "Ask one of the Agents in Feishu, then refresh this page.",
		"common.activityStoreFirstTurn": "The local activity store will be created by the first Agent turn.",
		"common.noDeliveryHistory": "No delivery history yet.",
		"common.noPatchHistory": "No Auto Patch history yet.",
		"common.noDeliveryActivity": "No scheduled delivery activity recorded yet.",
		"common.noPatchActivity": "No Auto Patch activity recorded yet.",
		"common.noAgentRolesSettings": "No agent roles available yet.",
		"common.noIntegrationKeys": "No local integration keys configured.",
		"common.valueFor": "Value for {{name}}",
		"common.revealValue": "Reveal value",
		"common.copyValue": "Copy value",
		"common.copyCode": "Copy code",
		"common.showFullscreen": "Show fullscreen",
		"common.closeFullscreen": "Close fullscreen",
		"common.zoomOut": "Zoom out",
		"common.resetView": "Reset view",
		"common.zoomIn": "Zoom in",
		"common.diagram": "Diagram",
		"common.image": "Image",
		"common.formattingTools": "Formatting tools",
		"common.documentBody": "Document body",
		"common.add": "Add",
		"common.navigation": "Lumon navigation",
		"common.dashboardSections": "Dashboard sections",
		"common.explainSetting": "Explain this setting",
		"common.originalMarkdown": "Original Markdown",
		"common.preview": "Preview",
		"common.live": "Live",
		"common.attempt": "Attempt {{number}}: {{duration}}",
		"common.overwriting": "Overwriting…",
		"common.overwriteRemote": "Overwrite remote",
		"common.remoteDecision": "Remote updates need your decision",
		"common.remoteConflictCopy": "Lumon committed local workspace changes, but the remote branch changed before the push. Review the remote changes before choosing whether to overwrite them.",
		"common.onlyTaskBugCards": "Only Task and Bug cards in the current active sprint are shown.",
		"common.noPendingPatchCards": "No pending Auto Patch Jira cards were found in the current active sprint.",
		"common.patchFlow": "Capture → repository → patch → publish",
		"common.retryDeliveryCopy": "This removes the Story worktrees, resets its Delivery and JIRA status, then starts a new run. The failed run and logs stay in history.",
		"common.repositoryGovernance": "Repository Governance",
		"common.addRepository": "Add repository",
		"common.repositoryIntro": "Connect repositories by Git URL. Lumon clones them into repos/, detects runtime and build tooling, then lets you approve the automation that may change or publish code.",
		"common.attentionNote": "Needs attention means uncommitted changes, a branch behind remote, or a diverged branch/sync.",
		"common.repositoryConfiguration": "Repository configuration",
		"common.unnamedRepository": "Unnamed repository",
		"common.generic": "Generic",
		"common.noBuildTool": "No build tool detected",
		"common.identityConnection": "Identity & connection",
		"common.identityConnectionHelp": "Detected locally; the default branch is the only editable connection setting.",
		"common.localPath": "Local path",
		"common.remote": "Remote",
		"common.gitStatus": "Git status",
		"common.branchSync": "Branch sync",
		"common.defaultBranch": "Default branch",
		"common.runtimeBuild": "Runtime & build",
		"common.runtimeBuildHelp": "Detected from repository files. These values are read-only until the repository changes.",
		"common.language": "Language",
		"common.java": "Java",
		"common.node": "Node",
		"common.buildTools": "Build tools",
		"common.notDetected": "Not detected",
		"common.automationPermissions": "Automation permissions",
		"common.frontendDeliveryDisabled": "Frontend delivery remains disabled globally and cannot be enabled here.",
		"common.autoScanFixes": "Auto Scan fixes",
		"common.autoScanFixesHelp": "Allow high-confidence Scan fixes and their configured publish flow.",
		"common.deliveryPermission": "Auto Delivery",
		"common.deliveryPermissionHelp": "Allow approved technical delivery work for this repository.",
		"common.patchPermission": "Auto Patch",
		"common.patchPermissionHelp": "Allow Jira-driven fixes and publishing for this repository.",
		"common.deliveryVerification": "Delivery verification",
		"common.deliveryVerificationHelp": "Choose what Lumon should run for this repository after implementation.",
		"common.policy": "Policy",
		"common.runVerification": "Run verification",
		"common.runVerificationHelp": "Use the automatic profile or your custom commands.",
		"common.skipVerification": "Skip verification",
		"common.skipVerificationHelp": "Do not run compile, static checks, or tests.",
		"common.executionSource": "Execution source",
		"common.automaticProfile": "Automatic profile",
		"common.automaticProfileHelp": "Detect commands from repository files at runtime.",
		"common.customCommands": "Custom commands",
		"common.customCommandsHelp": "Run only the commands entered below.",
		"common.checksToRun": "Checks to run",
		"common.compileChecks": "Compile & static checks",
		"common.compileChecksHelp": "Compile, syntax, typecheck, lint, or PMD checks.",
		"common.tests": "Tests",
		"common.testsHelp": "Unit, integration, and test-suite commands.",
		"common.commands": "Commands",
		"common.useSuggestedCommands": "Use {{count}} suggested command{{suffix}}",
		"common.oneCommandPerLine": "One command per line.",
		"common.cloneUrl": "Clone URL",
		"common.cloneInspect": "Clone and inspect",
		"common.addRepositoryDescription": "Lumon clones the Git URL, detects the branch and tooling, enables existing Scan and Delivery behavior, and authorizes Auto Patch by default.",
		"common.settingsSections": "Settings sections",
		"common.schedules": "Schedules",
		"common.agentConversations": "Agent conversations",
		"common.integrations": "Integrations",
		"common.configuredKeys": "configured keys",
		"settings.automation": "Automation",
		"settings.automationDescription": "Schedules and execution policies that decide when work can move.",
		"settings.agentTeam": "Agent team",
		"settings.agentTeamDescription": "Who speaks to people, what each role owns, and which conversations may mutate state.",
		"settings.projectOutput": "Project output",
		"settings.projectOutputDescription": "Defaults used when Mark and Milchick turn a request into a testable Story.",
		"settings.runtime": "Runtime & integrations",
		"settings.runtimeDescription": "Model selection, publish behavior, notifications, and local secret values.",
		"settings.nextAgentTeam": "Next: Agent team",
		"settings.nextProjectOutput": "Next: Project output",
		"settings.nextRuntime": "Next: Runtime & integrations",
		"settings.backAutomation": "Back to Automation",
		"settings.localConfiguration": "Local configuration",
		"settings.controlPlane": "01 · CONTROL PLANE",
		"settings.humanAgents": "02 · HUMAN-FACING AGENTS",
		"settings.businessOutput": "03 · BUSINESS OUTPUT",
		"settings.operatingDetails": "04 · OPERATING DETAILS",
		"settings.globalFeishuAgents": "Global Feishu agents",
		"settings.accessControl": "Access Control",
		"settings.accessControlDescription": "Who may talk to agents, and who may mutate (resolve findings, update schedules, start delivery). Add Allowed chat IDs to let Dylan/Milchick reply in those groups when @mentioned.",
		"settings.accessPerson": "Person",
		"settings.accessChat": "Group chat",
		"settings.selectPerson": "Select a person",
		"settings.selectChat": "Select a group chat",
		"settings.identityRoles": "Access for this identity",
		"settings.selectIdentityHelp": "Choose one identity, then edit the three access roles below.",
		"settings.canTalk": "Can talk to Agents",
		"settings.canMutate": "Can run mutations",
		"settings.canAdmin": "Can administer Agents",
		"settings.accessSummary": "Configured identities",
		"settings.identityCount": "{{count}} identity records",
		"settings.rolesApplied": "roles",
		"settings.agentCoreDescription": "Core controls are editable here. Role ownership, safety boundaries, and SOUL files stay managed by the Agent registry.",
		"settings.responsibility": "Responsibility",
		"settings.legacyWarning": "Legacy allow mode is unsafe for local agents. Prefer per-agent Access & Exposure with default_policy=deny.",
		"settings.recentPeople": "Recent people",
		"settings.recentChats": "Recent chats",
		"settings.addMutationUser": "Click to add as mutation user",
		"settings.allowChat": "Click to allow the chat",
		"settings.noRecentPeople": "No recent Feishu people yet. Message Dylan or Mark once, then refresh Settings.",
		"settings.generationLanguage": "Generation language",
		"settings.generationDescription": "Controls the language Mark writes into the Feishu Spreadsheet for this project. Traditional Chinese is the default for mbpass.",
		"settings.afterGeneration": "After changing language or sheet, ask Milchick/Mark to re-generate the story so new rows use the selected sheet.",
		"settings.executionDescription": "Choose a preset or enter a custom Cursor model ID. Custom values must be supported by Cursor; Lumon does not validate model availability.",
		"settings.automationOutcome": "Automation outcome",
		"settings.notificationsDescription": "Control whether Scan and Delivery post cards to the configured Feishu webhook. The webhook URL still lives under Variable Keys.",
		"settings.storedWorkspace": "Stored only in this workspace",
		"settings.availableKeys": "Available keys",
		"settings.availableKeysDescription": "Reveal a value to inspect it, or enter a replacement directly. Values are saved without display quotes.",
		"settings.revealReplacement": "Reveal or enter a replacement value",
		"settings.unsavedChanges": "You have unsaved changes",
		"settings.allSaved": "All changes saved",
		"settings.deliveryPaused": "Delivery polling is paused.",
		"settings.patchPaused": "Auto Patch polling is paused.",
		"settings.deliveryStatusHelp": "Select every Jira status that may start Auto Delivery. The Story must also be Business Ready, Technical Approved, and not already running.",
		"settings.deliveryStatusNote": "Select To Do, Backlog, In Progress, or any other eligible Jira status. On failure, Lumon moves the Jira card to the selected Block status and adds a Needs attention comment.",
		"settings.patchStatusNote": "Only Task and Bug cards are captured. Blocked cards retry after a new external Jira comment.",
		"settings.scanDefaultDescription": "No recurring scan is configured.",
		"settings.direct": "Direct",
		"settings.merge": "Merge",
		"settings.pullRequest": "PR",
		"settings.openPullRequest": "Open pull request",
		"settings.mergeAfterPullRequest": "Merge after pull request",
		"settings.pushDirectly": "Push directly to main branch",
		"settings.feishuNotifications": "Feishu notifications",
		"settings.allowedChatIds": "Allowed chat IDs",
		"settings.allowedUserIds": "Allowed user IDs",
		"settings.mutationUserIds": "Mutation user IDs",
		"settings.adminUserIds": "Admin user IDs",
		"settings.allowedChatHelp": "Whitelist group chats. Dylan/Milchick stay DM-only unless a chat is listed here; @mention is still required in groups.",
		"settings.allowedUserHelp": "Empty = all users may ask read-only questions.",
		"settings.mutationUserHelp": "Required for resolve / schedule update / delivery start. Fail-closed when empty.",
		"settings.adminUserHelp": "Admins can also mutate.",
		"settings.appSecretRequired": "Required for Feishu client login.",
		"settings.keepSecret": "Leave blank to keep current secret",
		"settings.enterSecret": "Enter app secret",
		"settings.runtimeIdentityHelp": "Runtime identity is managed by the Agent registry.",
		"settings.workflowOwnershipHelp": "Workflow ownership is managed by the Agent registry.",
		"settings.publishDescription": "Direct push uses the repository credentials already configured for Git; PR and Merge use GitHub CLI. Auto Scan keeps a PR review gate and does not support direct push.",
		"settings.deploymentTracking": "Deployment tracking",
		"settings.deploymentTrackingDescription": "After publish, follow the configured CI/CD run and report only the actual deployment result. Credentials stay in local environment variables.",
		"settings.deploymentProvider": "Provider",
		"settings.deploymentDisabled": "Disabled",
		"settings.jenkins": "Jenkins",
		"settings.githubActions": "GitHub Actions",
		"settings.pollInterval": "Poll interval (seconds)",
		"settings.deploymentTimeout": "Timeout (seconds)",
		"settings.deploymentProviderHelp": "The CI/CD system whose deployment run should be observed after publish.",
		"settings.deploymentOwner": "Tracking owner",
		"settings.deploymentOwnerValue": "Milchick · Engineering Operations Manager",
		"settings.deploymentOwnerHelp": "Milchick owns the follow-up decision. Source or delivery failures go to Mark; Jira repair work goes to Irving; unclear infrastructure failures are reported for a human decision.",
		"settings.deploymentFailureHandling": "The host worker polls the provider. Milchick receives the terminal evidence and decides the next owner; no failure is hard-coded to Mark.",
		"settings.credentials": "Credentials",
		"settings.configured": "Configured",
		"settings.notConfigured": "Not configured",
		"settings.localGhLogin": "Local gh login",
		"settings.jenkinsPipeline": "Jenkins deployment pipeline",
		"settings.jenkinsPipelineHelp": "Required to identify the Jenkins pipeline to observe. Example: folder/job-name. Lumon does not use this field to run code.",
		"settings.jenkinsCredentials": "Set JENKINS_URL and JENKINS_AUTH in Variable Keys. Values stay in the workspace environment and are never written to delivery.json.",
		"settings.githubCredentials": "GitHub Actions uses the workspace runner's local gh login. No token is entered or stored here.",
		"settings.githubRepository": "GitHub repository",
		"settings.githubWorkflow": "Workflow (optional)",
		"label.deployment": "Deployment",
		"label.provider": "Provider",
		"label.lastChecked": "Last checked",
		"action.openDeployment": "Open deployment",
		"editor.heading": "Heading",
		"editor.editLink": "Edit link URL",
		"editor.linkUrl": "Link URL",
		"editor.bold": "Bold",
		"editor.italic": "Italic",
		"editor.link": "Link — Shift+click a link to place the caret, then edit",
		"editor.list": "List",
		"editor.code": "Code",
		"prompt.original": "Original Markdown",
		"prompt.preview": "Preview",
		"customModel.enter": "Enter a custom Cursor model",
		"customModel.id": "Cursor model ID",
		"customModel.placeholder": "e.g. cursor-grok-4.5-medium",
		"customModel.copy": "Lumon does not validate model availability. The value will be used on the next run.",
		"customModel.edit": "Edit custom model",
		"customModel.option": "Custom Cursor model ID…",
		"customModel.badge": "Custom",
		"customModel.help": "Use a model ID supported by Cursor.",
		"status.completed": "Completed",
		"status.passed": "Passed",
		"status.failed": "Failed",
		"status.skipped": "Skipped",
		"status.open": "Open",
		"status.inProgress": "In progress",
		"status.awaitingDeploy": "Awaiting deployment",
		"status.running": "Running",
		"status.active": "Active",
		"status.notSet": "Not set",
		"status.notConfigured": "Not configured",
		"status.resolved": "Resolved",
		"status.reopened": "Reopened",
		"status.synced": "Synced",
		"status.ignored": "Ignored",
		"status.blocked": "Blocked",
		"status.pending": "Pending",
		"status.prOpen": "PR open",
		"status.notStarted": "Not started",
		"status.devDone": "Dev done",
		"status.approved": "Approved",
		"status.ready": "Ready",
		"status.draft": "Draft",
		"status.done": "Done",
		"status.clarifying": "Clarifying",
		"status.changed": "Changed",
		"label.business": "Business",
		"label.technical": "Technical",
		"workflow.auto_scan.feature": "Auto Scan",
		"workflow.auto_scan.mission": "Find recurring engineering risk and turn it into review-ready evidence.",
		"workflow.auto_scan.input": "Repositories, scan window, risk signals",
		"workflow.auto_scan.output": "Findings, severity, links, and next questions",
		"workflow.auto_delivery.feature": "Auto Delivery",
		"workflow.auto_delivery.mission": "Move an approved Story through implementation, verification, and delivery.",
		"workflow.auto_delivery.input": "Ready Story, approved plan, delivery policy",
		"workflow.auto_delivery.output": "Commits, checks, PR/merge result, or a clear blocker",
		"workflow.auto_patch.feature": "Auto Patch",
		"workflow.auto_patch.mission": "Pick up Jira Task/Bug work, apply a focused fix, and hand it off safely.",
		"workflow.auto_patch.input": "Eligible Jira card, repository guardrails",
		"workflow.auto_patch.output": "Patch evidence, verification, and PR/direct-push result",
		"workflow.manager.feature": "Manager",
		"workflow.manager.mission": "Clarify intent, create the right work item, and coordinate the three capability owners.",
		"workflow.manager.input": "Business request, missing decisions, loop state",
		"workflow.manager.output": "A question, a work card, or a routed execution request",
		"label.autoScan": "Auto Scan",
		"label.autoDelivery": "Auto Delivery",
		"label.autoPatch": "Auto Patch",
		"label.manager": "Manager",
		"label.entryPoint": "Entry point",
		"label.feishuEntry": "User / Feishu entry",
		"label.managerLayer": "Coordination layer",
		"label.capabilityOwners": "Capability owners",
		"label.role": "Role",
		"label.input": "Input",
		"label.output": "Output",
		"label.owns": "Owns",
		"label.receives": "Receives",
		"label.returns": "Returns",
		"label.gateway": "Gateway",
		"label.agentsReady": "Agents ready",
		"label.workflowsActive": "Workflows active",
		"label.questionsWaiting": "Questions waiting",
		"label.agentRoles": "Agent roles",
		"label.recordedTurns": "Recorded turns",
		"label.processedQuestions": "Questions handled",
		"label.averageDuration": "Average duration",
		"label.needsAttention": "Needs attention",
		"label.rolesSeen": "Roles seen",
		"label.businessReadyCapabilities": "Three human-owned capabilities",
		"label.conversationClear": "Conversation is clear",
		"label.unanswered": "{{count}} unanswered",
		"label.sharedRuntime": "{{count}} roles · shared runtime",
		"label.currentStory": "Current story",
		"label.status": "Status",
		"label.elapsed": "Elapsed",
		"label.finished": "Finished",
		"label.jiraCard": "Jira card",
		"label.branch": "Branch",
		"label.repositories": "Repositories",
		"label.started": "Started",
		"label.issues": "Issues",
		"label.duration": "Duration",
		"label.artifacts": "Artifacts",
		"label.story": "Story",
		"label.pullRequests": "Pull requests",
		"label.checks": "Checks",
		"label.operation": "Operation",
		"label.finishedAt": "Finished",
		"label.log": "Log",
		"label.summary": "Summary",
		"label.jira": "Jira",
		"label.trace": "Trace",
		"label.repository": "Repository",
		"label.localCommit": "Local commit",
		"label.roleId": "Role id",
		"label.workflow": "Workflow",
		"label.prompt": "prompt",
		"label.conversation": "Conversation",
		"label.typingReaction": "Typing reaction",
		"label.lookbackDays": "Lookback, days",
		"label.cron": "Five-field cron",
		"label.intervalMinutes": "Interval, minutes",
		"label.eligibleStatuses": "Eligible JIRA statuses",
		"label.moveStarted": "Move to when started",
		"label.moveCompleted": "Move to when completed",
		"label.moveFailed": "Move to when failed",
		"label.moveBlocked": "Move to when blocked",
		"label.outputLanguage": "Output language",
		"label.languageGeneration": "Generation language",
		"label.spreadsheetTab": "Spreadsheet tab name",
		"label.spreadsheetToken": "Spreadsheet token / URL",
		"label.cursorModel": "Cursor model",
		"label.softTimeout": "Soft timeout, seconds",
		"label.hardTimeout": "Hard timeout, seconds",
		"label.maxJobs": "Max concurrent jobs",
		"label.soulVersion": "SOUL version",
		"label.feishuAppId": "Feishu App ID",
		"label.feishuAppSecret": "Feishu App Secret",
		"label.completed": "Completed",
		"label.openFindings": "Open findings",
		"label.successfulScan": "Successful Scan · 7d",
		"label.failed7d": "Failed · 7d",
		"label.lookbackWindow": "Lookback window",
		"label.conversationAndActions": "Conversation and actions available",
		"label.conversationPaused": "Conversation is paused in Settings",
		"label.credentialsRequired": "Credentials are required",
		"label.requestResult": "Request + result",
		"label.resultCaptured": "Result captured · request predates transcript capture",
		"label.traceOnly": "Trace only",
		"label.executionTrail": "Execution trail",
		"label.debugDetails": "Debug details",
		"label.promptNotCaptured": "This runtime did not capture the original prompt.",
		"label.olderTrace": "This older trace has an outcome, but its incoming message was not captured by that runtime version.",
		"label.noFinalResponse": "No final response text was retained; open the source trace in the Agent logs if deeper evidence is needed.",
		"label.activityRetention": "Only bounded local request/result text is shown here. Trace IDs and raw execution evidence remain available in the local Agent store.",
		"label.high": "High",
		"label.medium": "Medium",
		"label.low": "Low",
		"label.untitledFinding": "Untitled finding",
		"label.unknownRepository": "Unknown repository",
		"label.reasonOptional": "Reason (optional)",
		"label.ignoreQuestion": "Mark this finding as ignored?",
		"label.ignorePlaceholder": "Why is this safe to ignore?",
		"label.noSnippet": "No code snippet was captured for this historical finding.",
		"label.notRecorded": "Not recorded.",
		"label.notStarted": "Awaiting delivery trigger",
		"label.running": "Running",
		"label.pending": "Pending",
		"label.stopped": "Stopped",
		"label.needsAttentionState": "Needs attention",
		"label.startedAt": "Started {{value}}",
		"label.finishedAtValue": "Finished {{value}}",
		"label.requested": "Request",
		"label.result": "Result",
		"label.noLog": "No log content recorded.",
		"label.noSchedulerLog": "No scheduler output recorded.",
		"label.noSummary": "No summary recorded.",
		"label.recentRawOutput": "Recent raw output",
		"label.close": "Close",
		"label.checksPassed": "{{count}} passed",
		"label.checksFailed": "{{count}} failed",
		"label.checksSkipped": "{{count}} skipped",
		"label.verification": "Verification",
		"label.checksTitle": "Checks",
		"heading.managerOverview": "Manager overview",
		"heading.agentActivity": "Agent activity",
		"heading.conversationRecords": "Conversation records",
		"heading.agentRoster": "Agent roster",
		"heading.agentTeam": "Agent team & workflows",
		"heading.agentArchitecture": "Agent architecture",
		"heading.workflowControl": "Workflow control",
		"heading.questionsWaiting": "Questions waiting for you",
		"heading.scanHistory": "Scan History",
		"heading.trackedFindings": "Tracked Findings",
		"heading.currentProgress": "Current Progress",
		"heading.deliveryHistory": "Delivery History",
		"heading.schedulerActivity": "Scheduler Activity",
		"heading.patchHistory": "Patch History",
		"heading.stories": "Stories",
		"heading.workspaceSettings": "Workspace settings",
		"heading.agentRoles": "Agent Roles",
		"heading.automationSchedules": "Automation Schedules",
		"heading.executionModels": "Execution Models",
		"heading.publishPolicy": "Publish Policy",
		"heading.notifications": "Notifications",
		"heading.variableKeys": "Variable Keys",
		"heading.testCases": "Test Cases",
		"heading.workflow": "{{feature}} Workflow",
		"action.openSettings": "Open Settings",
		"action.configureAgent": "Configure agent",
		"action.manageCapture": "Manage capture",
		"action.viewActivity": "View activity",
		"action.inspect": "Inspect {{feature}}",
		"action.startScan": "Start scan",
		"action.runCycle": "Run one cycle",
		"action.viewRawLog": "View raw log",
		"action.openLog": "Open failure log",
		"action.markIgnored": "Mark ignored",
		"action.viewDetail": "View detail",
		"action.hideDetail": "Hide detail",
		"action.pullRequest": "Pull request",
		"action.startDelivery": "Start delivery",
		"action.saveChanges": "Save changes",
		"action.savePrompt": "Save prompt",
		"action.searchStories": "Search stories",
		"action.filterStories": "Filter stories",
		"action.showingReadyStories": "Showing business-ready stories",
		"action.filterReadyStories": "Filter business-ready stories",
		"action.exitFullscreen": "Exit full screen",
		"action.viewFullscreen": "View full screen",
		"action.start": "Start",
		"action.save": "Save",
		"action.runScan": "Start a scan?",
		"action.confirmScan": "Confirm scan start",
		"action.scanBody": "This will launch an auto-scan for {{project}}.",
		"action.scanConfirmBody": "Are you sure you want to start a scan for {{project}} now? A scan agent will run against the configured repositories."
	},
	"zh-Hans": {
		"language.label": "语言",
		"language.en": "English",
		"language.zhHans": "简体中文",
		"language.zhHant": "繁體中文",
		"nav.overview": "总览",
		"nav.activity": "活动记录",
		"nav.scan": "自动扫描",
		"nav.delivery": "自动交付",
		"nav.patch": "自动修复",
		"nav.observatory": "观测台",
		"nav.repositories": "代码仓库",
		"nav.prompts": "工作流",
		"nav.settings": "设置",
		"context.overview.title": "管理者总览",
		"context.overview.description": "查看 Agent 职责、工作流健康度和下一项需要人工决策的事项。",
		"context.activity.title": "Agent 活动",
		"context.activity.description": "查看对话记录、处理结果以及每次 Agent 执行背后的证据。",
		"context.scan.title": "自动扫描",
		"context.scan.description": "查看扫描历史并管理已跟踪的问题。",
		"context.delivery.title": "自动交付",
		"context.delivery.description": "查看 Story 执行、验证和 Pull Request 交付。",
		"context.patch.title": "自动修复",
		"context.patch.description": "查看 Jira Task/Bug 捕获、聚焦修复和安全交接。",
		"context.observatory.title": "观测台",
		"context.observatory.description": "浏览和编辑 Story 说明与技术方案。",
		"context.repositories.title": "代码仓库",
		"context.repositories.description": "管理本地仓库、自动化权限和交付验证策略。",
		"context.prompts.title": "工作流",
		"context.prompts.description": "查看各项本地自动化背后的提示词、脚本、控制点和恢复路径。",
		"context.settings.title": "设置",
		"context.settings.description": "配置工作区、调度和本地集成。",
		"common.updated": "更新于 {{value}}",
		"common.syncing": "同步中…",
		"common.project": "项目",
		"common.currentProject": "当前项目",
		"common.openSettings": "打开设置",
		"common.manageCapture": "管理记录",
		"common.loadingWorkspace": "正在加载本地工作区状态…",
		"common.expandNavigation": "展开导航",
		"common.collapseNavigation": "收起导航",
		"common.version": "版本 {{value}}",
		"common.staticReport": "静态报告模式：交互操作不可用。",
		"common.unableLoadState": "无法加载 Dashboard 状态",
		"common.requestFailed": "请求失败",
		"common.unsavedSettings": "设置中有未保存的更改，要不保存就离开吗？",
		"common.unsavedObservatory": "观测台有未保存的更改，要不保存就离开吗？",
		"common.noData": "暂无数据。",
		"common.cancel": "取消",
		"common.close": "关闭",
		"common.later": "稍后",
		"common.save": "保存",
		"common.saving": "保存中…",
		"common.confirm": "确认",
		"common.continue": "继续",
		"common.start": "开始",
		"common.stop": "停止",
		"common.retry": "重试",
		"common.loading": "加载中…",
		"common.enabled": "已启用",
		"common.paused": "已暂停",
		"common.active": "运行中",
		"common.off": "关闭",
		"common.all": "全部",
		"common.clear": "清除",
		"common.selected": "已选择 {{count}} 项",
		"common.statusesSelected": "已选择 {{count}} 个状态",
		"common.previous": "上一页",
		"common.next": "下一页",
		"common.pageOf": "第 {{page}} 页，共 {{count}} 页",
		"common.showing": "显示 {{count}} 项",
		"common.debugDetails": "调试详情",
		"common.originalPrompt": "发送给 Agent 的原始提示词",
		"common.records": "{{count}} 条记录",
		"common.runs": "{{count}} 次运行",
		"common.recentEvents": "最近 {{count}} 个事件",
		"common.yes": "是",
		"common.no": "否",
		"common.unknown": "未知",
		"common.workspace": "工作区",
		"common.agent": "Agent",
		"common.clarification": "澄清",
		"common.manager": "Manager",
		"common.you": "你",
		"common.trace": "Trace",
		"common.viewActivity": "查看活动",
		"common.viewLog": "查看日志",
		"common.viewTrace": "查看 Trace",
		"common.open": "打开",
		"common.inspect": "查看",
		"common.noAgentRoles": "暂无可用的 Agent 角色。",
		"common.noAgentQuestions": "没有待回答的 Agent 问题。",
		"common.noConversationRecords": "没有符合筛选条件的对话记录。",
		"common.noFindings": "没有符合该状态的问题。",
		"common.noStoriesFilter": "没有符合筛选条件的 Story。",
		"common.noStories": "文档仓库中没有找到 Story。",
		"common.selectStory": "选择一个 Story 查看。",
		"common.noAgentHistory": "暂无 Agent 对话存储。网关启动后，新飞书对话会显示在这里。",
		"common.askAgents": "在飞书中询问 Agent，然后刷新此页面。",
		"common.activityStoreFirstTurn": "首次 Agent 对话后会创建本地活动记录。",
		"common.noDeliveryHistory": "暂无交付历史。",
		"common.noPatchHistory": "暂无自动修复历史。",
		"common.noDeliveryActivity": "暂无已记录的定时交付活动。",
		"common.noPatchActivity": "暂无已记录的自动修复活动。",
		"common.noAgentRolesSettings": "暂无可用的 Agent 角色。",
		"common.noIntegrationKeys": "未配置本地集成密钥。",
		"common.valueFor": "{{name}} 的值",
		"common.revealValue": "显示值",
		"common.copyValue": "复制值",
		"common.copyCode": "复制代码",
		"common.showFullscreen": "全屏显示",
		"common.closeFullscreen": "关闭全屏",
		"common.zoomOut": "缩小",
		"common.resetView": "重置视图",
		"common.zoomIn": "放大",
		"common.diagram": "图表",
		"common.image": "图片",
		"common.formattingTools": "格式工具",
		"common.documentBody": "文档正文",
		"common.add": "添加",
		"common.navigation": "Lumon 导航",
		"common.dashboardSections": "Dashboard 分区",
		"common.explainSetting": "解释此设置",
		"common.originalMarkdown": "原始 Markdown",
		"common.preview": "预览",
		"common.live": "实时",
		"common.attempt": "第 {{number}} 次：{{duration}}",
		"common.overwriting": "覆盖中…",
		"common.overwriteRemote": "覆盖远程版本",
		"common.remoteDecision": "远程更新需要你的决定",
		"common.remoteConflictCopy": "Lumon 已提交本地工作区变更，但远程分支在推送前发生了变化。请先检查远程变更，再决定是否覆盖。",
		"common.onlyTaskBugCards": "这里只显示当前活跃 Sprint 中的 Task 和 Bug 卡片。",
		"common.noPendingPatchCards": "当前活跃 Sprint 中没有待处理的 Auto Patch Jira 卡片。",
		"common.patchFlow": "捕获 → 仓库 → 修复 → 发布",
		"common.retryDeliveryCopy": "这会移除 Story 工作树，重置其 Delivery 和 Jira 状态，然后启动新一轮运行。失败运行和日志仍会保留在历史记录中。",
		"common.repositoryGovernance": "仓库治理",
		"common.addRepository": "添加仓库",
		"common.repositoryIntro": "通过 Git URL 连接仓库。Lumon 会将其克隆到 repos/，检测运行时和构建工具，然后让你批准可以修改或发布代码的自动化能力。",
		"common.attentionNote": "“需要关注”表示存在未提交变更、分支落后远程，或分支/同步发生分叉。",
		"common.repositoryConfiguration": "仓库配置",
		"common.unnamedRepository": "未命名仓库",
		"common.generic": "通用",
		"common.noBuildTool": "未检测到构建工具",
		"common.identityConnection": "身份与连接",
		"common.identityConnectionHelp": "从本地检测得到；只有默认分支是可编辑的连接设置。",
		"common.localPath": "本地路径",
		"common.remote": "远程地址",
		"common.gitStatus": "Git 状态",
		"common.branchSync": "分支同步",
		"common.defaultBranch": "默认分支",
		"common.runtimeBuild": "运行时与构建",
		"common.runtimeBuildHelp": "从仓库文件中检测得到。仓库发生变化前，这些值为只读。",
		"common.language": "语言",
		"common.java": "Java",
		"common.node": "Node",
		"common.buildTools": "构建工具",
		"common.notDetected": "未检测到",
		"common.automationPermissions": "自动化权限",
		"common.frontendDeliveryDisabled": "前端交付在全局策略中保持关闭，无法在这里启用。",
		"common.autoScanFixes": "Auto Scan 修复",
		"common.autoScanFixesHelp": "允许高置信度的 Scan 修复及其配置的发布流程。",
		"common.deliveryPermission": "Auto Delivery",
		"common.deliveryPermissionHelp": "允许此仓库执行已批准的技术交付工作。",
		"common.patchPermission": "Auto Patch",
		"common.patchPermissionHelp": "允许针对 Jira 驱动的修复并发布。",
		"common.deliveryVerification": "交付验证",
		"common.deliveryVerificationHelp": "选择实现完成后 Lumon 应为此仓库运行哪些验证。",
		"common.policy": "策略",
		"common.runVerification": "运行验证",
		"common.runVerificationHelp": "使用自动配置或你自定义的命令。",
		"common.skipVerification": "跳过验证",
		"common.skipVerificationHelp": "不运行编译、静态检查或测试。",
		"common.executionSource": "执行来源",
		"common.automaticProfile": "自动配置",
		"common.automaticProfileHelp": "运行时从仓库文件中检测命令。",
		"common.customCommands": "自定义命令",
		"common.customCommandsHelp": "只运行下面输入的命令。",
		"common.checksToRun": "要运行的检查",
		"common.compileChecks": "编译与静态检查",
		"common.compileChecksHelp": "编译、语法、类型检查、Lint 或 PMD 检查。",
		"common.tests": "测试",
		"common.testsHelp": "单元测试、集成测试和测试套件命令。",
		"common.commands": "命令",
		"common.useSuggestedCommands": "使用 {{count}} 条建议命令{{suffix}}",
		"common.oneCommandPerLine": "每行一条命令。",
		"common.cloneUrl": "克隆 URL",
		"common.cloneInspect": "克隆并检查",
		"common.addRepositoryDescription": "Lumon 会克隆 Git URL、检测分支和工具，启用现有的 Scan 与 Delivery 行为，并默认授权 Auto Patch。",
		"common.settingsSections": "设置分区",
		"common.schedules": "调度",
		"common.agentConversations": "Agent 对话",
		"common.integrations": "集成",
		"common.configuredKeys": "个已配置密钥",
		"settings.automation": "自动化",
		"settings.automationDescription": "决定工作何时可以推进的调度和执行策略。",
		"settings.agentTeam": "Agent 团队",
		"settings.agentTeamDescription": "谁与人沟通、各角色负责什么，以及哪些对话可以修改状态。",
		"settings.projectOutput": "项目产出",
		"settings.projectOutputDescription": "Mark 和 Milchick 将请求转成可测试 Story 时使用的默认设置。",
		"settings.runtime": "运行时与集成",
		"settings.runtimeDescription": "模型选择、发布行为、通知和本地密钥值。",
		"settings.nextAgentTeam": "下一步：Agent 团队",
		"settings.nextProjectOutput": "下一步：项目产出",
		"settings.nextRuntime": "下一步：运行时与集成",
		"settings.backAutomation": "返回自动化",
		"settings.localConfiguration": "本地配置",
		"settings.controlPlane": "01 · 控制面",
		"settings.humanAgents": "02 · 面向人的 Agent",
		"settings.businessOutput": "03 · 业务产出",
		"settings.operatingDetails": "04 · 运行细节",
		"settings.globalFeishuAgents": "全局飞书 Agent",
		"settings.accessControl": "访问控制",
		"settings.accessControlDescription": "谁可以与 Agent 对话、谁可以修改状态（解决问题、更新调度、启动交付）。添加允许的群聊 ID 后，Dylan/Milchick 才能在被 @提及时回复这些群聊。",
		"settings.accessPerson": "用户",
		"settings.accessChat": "群聊",
		"settings.selectPerson": "选择用户",
		"settings.selectChat": "选择群聊",
		"settings.identityRoles": "此身份的访问权限",
		"settings.selectIdentityHelp": "选择一个身份，然后编辑下面的三项访问权限。",
		"settings.canTalk": "可以与 Agent 对话",
		"settings.canMutate": "可以执行变更操作",
		"settings.canAdmin": "可以管理 Agent",
		"settings.accessSummary": "已配置身份",
		"settings.identityCount": "{{count}} 个身份记录",
		"settings.rolesApplied": "项权限",
		"settings.agentCoreDescription": "这里只编辑核心控制项。角色归属、安全边界和 SOUL 文件仍由 Agent 注册表管理。",
		"settings.responsibility": "职责",
		"settings.legacyWarning": "旧版 allow 模式对本地 Agent 不安全。建议使用按 Agent 配置的 Access & Exposure，并将 default_policy 设为 deny。",
		"settings.recentPeople": "最近联系人",
		"settings.recentChats": "最近群聊",
		"settings.addMutationUser": "点击添加为可变更用户",
		"settings.allowChat": "点击允许此群聊",
		"settings.noRecentPeople": "暂无最近的飞书联系人。先给 Dylan 或 Mark 发一条消息，再刷新设置。",
		"settings.generationLanguage": "生成语言",
		"settings.generationDescription": "控制 Mark 为此项目写入飞书电子表格的语言。mbpass 默认使用繁体中文。",
		"settings.afterGeneration": "修改语言或表格后，请让 Milchick/Mark 重新生成 Story，使新行使用选定的表格。",
		"settings.executionDescription": "选择预设模型，或输入自定义 Cursor 模型 ID。自定义值必须受 Cursor 支持；Lumon 不会验证模型是否可用。",
		"settings.automationOutcome": "自动化结果",
		"settings.notificationsDescription": "控制 Scan 和 Delivery 是否向已配置的飞书 Webhook 发布卡片。Webhook URL 仍位于变量密钥中。",
		"settings.storedWorkspace": "仅存储在此工作区",
		"settings.availableKeys": "可用密钥",
		"settings.availableKeysDescription": "显示值以检查，或直接输入替换值。保存时不会包含显示引号。",
		"settings.revealReplacement": "显示或输入替换值",
		"settings.unsavedChanges": "有未保存的更改",
		"settings.allSaved": "所有更改已保存",
		"settings.deliveryPaused": "交付轮询已暂停。",
		"settings.patchPaused": "Auto Patch 轮询已暂停。",
		"settings.deliveryStatusHelp": "选择所有可以启动 Auto Delivery 的 Jira 状态。Story 还必须处于 Business Ready、Technical Approved 且未在运行。",
		"settings.deliveryStatusNote": "选择 To Do、Backlog、In Progress 或其他符合条件的 Jira 状态。失败时，Lumon 会将 Jira 卡片流转到选定的 Block 状态，并添加需要关注的评论。",
		"settings.patchStatusNote": "只捕获 Task 和 Bug 卡片。阻塞卡片会在收到新的外部 Jira 评论后重试。",
		"settings.scanDefaultDescription": "尚未配置周期性扫描。",
		"settings.direct": "直接推送",
		"settings.merge": "合并",
		"settings.pullRequest": "PR",
		"settings.openPullRequest": "打开 Pull Request",
		"settings.mergeAfterPullRequest": "在 Pull Request 后合并",
		"settings.pushDirectly": "直接推送到 main 分支",
		"settings.feishuNotifications": "飞书通知",
		"settings.allowedChatIds": "允许的群聊 ID",
		"settings.allowedUserIds": "允许的用户 ID",
		"settings.mutationUserIds": "可变更用户 ID",
		"settings.adminUserIds": "管理员用户 ID",
		"settings.allowedChatHelp": "将群聊加入白名单。除非群聊已列出，否则 Dylan/Milchick 只能私聊；在群聊中仍必须 @提及。",
		"settings.allowedUserHelp": "为空表示所有用户都可以询问只读问题。",
		"settings.mutationUserHelp": "解决问题、更新调度和启动交付时必需。为空时默认拒绝。",
		"settings.adminUserHelp": "管理员也可以执行变更操作。",
		"settings.appSecretRequired": "飞书客户端登录必需。",
		"settings.keepSecret": "留空以保留当前密钥",
		"settings.enterSecret": "输入 App Secret",
		"settings.runtimeIdentityHelp": "运行时身份由 Agent 注册表管理。",
		"settings.workflowOwnershipHelp": "工作流归属由 Agent 注册表管理。",
		"settings.publishDescription": "直接推送使用已配置的 Git 仓库凭证；PR 和合并使用 GitHub CLI。Auto Scan 保留 PR 审查门禁，不支持直接推送。",
		"settings.deploymentTracking": "部署状态跟踪",
		"settings.deploymentTrackingDescription": "发布后跟踪配置好的 CI/CD 运行，并只在部署真正完成后回报结果。凭证保留在本地环境变量中。",
		"settings.deploymentProvider": "提供商",
		"settings.deploymentDisabled": "未启用",
		"settings.jenkins": "Jenkins",
		"settings.githubActions": "GitHub Actions",
		"settings.pollInterval": "轮询间隔（秒）",
		"settings.deploymentTimeout": "超时（秒）",
		"settings.deploymentProviderHelp": "发布后需要观察哪个 CI/CD 系统的部署运行。",
		"settings.deploymentOwner": "跟踪负责人",
		"settings.deploymentOwnerValue": "Milchick · 工程运营经理",
		"settings.deploymentOwnerHelp": "Milchick 负责判断后续归属：源码或交付失败交给 Mark，Jira 修复交给 Irving，基础设施或无法判断的问题回报人工决策。",
		"settings.deploymentFailureHandling": "后台 worker 负责轮询提供商；Milchick 接收最终证据并决定下一位负责人，不再把所有失败硬编码交给 Mark。",
		"settings.credentials": "凭证",
		"settings.configured": "已配置",
		"settings.notConfigured": "未配置",
		"settings.localGhLogin": "本地 gh 登录",
		"settings.jenkinsPipeline": "Jenkins 部署流水线",
		"settings.jenkinsPipelineHelp": "用于定位需要观察的 Jenkins 流水线。例如：folder/job-name。Lumon 不会用此字段执行代码。",
		"settings.jenkinsCredentials": "请在变量密钥中配置 JENKINS_URL 和 JENKINS_AUTH。值保留在工作区环境中，不会写入 delivery.json。",
		"settings.githubCredentials": "GitHub Actions 使用工作区运行器的本地 gh 登录状态。这里不输入也不保存 Token。",
		"settings.githubRepository": "GitHub 仓库",
		"settings.githubWorkflow": "Workflow（可选）",
		"label.deployment": "部署",
		"label.provider": "提供商",
		"label.lastChecked": "最近检查",
		"action.openDeployment": "打开部署",
		"editor.heading": "标题",
		"editor.editLink": "编辑链接 URL",
		"editor.linkUrl": "链接 URL",
		"editor.bold": "粗体",
		"editor.italic": "斜体",
		"editor.link": "链接 — Shift+点击链接可定位光标，然后编辑",
		"editor.list": "列表",
		"editor.code": "代码",
		"prompt.original": "原始 Markdown",
		"prompt.preview": "预览",
		"customModel.enter": "输入自定义 Cursor 模型",
		"customModel.id": "Cursor 模型 ID",
		"customModel.placeholder": "例如：cursor-grok-4.5-medium",
		"customModel.copy": "Lumon 不会验证模型是否可用，该值将在下一次运行时使用。",
		"customModel.edit": "编辑自定义模型",
		"customModel.option": "自定义 Cursor 模型 ID…",
		"customModel.badge": "自定义",
		"customModel.help": "使用 Cursor 支持的模型 ID。",
		"status.completed": "已完成",
		"status.passed": "通过",
		"status.failed": "失败",
		"status.skipped": "已跳过",
		"status.open": "开放",
		"status.inProgress": "进行中",
		"status.awaitingDeploy": "等待部署",
		"status.running": "运行中",
		"status.active": "活跃",
		"status.notSet": "未设置",
		"status.notConfigured": "未配置",
		"status.resolved": "已解决",
		"status.reopened": "已重新打开",
		"status.synced": "已同步",
		"status.ignored": "已忽略",
		"status.blocked": "已阻塞",
		"status.pending": "待处理",
		"status.prOpen": "PR 已打开",
		"status.notStarted": "未开始",
		"status.devDone": "开发完成",
		"status.approved": "已批准",
		"status.ready": "就绪",
		"status.draft": "草稿",
		"status.done": "完成",
		"status.clarifying": "澄清中",
		"status.changed": "已变更",
		"label.business": "业务",
		"label.technical": "技术",
		"workflow.auto_scan.feature": "自动扫描",
		"workflow.auto_scan.mission": "发现反复出现的工程风险，并整理成可供评审的证据。",
		"workflow.auto_scan.input": "代码仓库、扫描窗口、风险信号",
		"workflow.auto_scan.output": "问题、严重程度、链接和后续问题",
		"workflow.auto_delivery.feature": "自动交付",
		"workflow.auto_delivery.mission": "推动已批准的 Story 完成实现、验证和交付。",
		"workflow.auto_delivery.input": "就绪 Story、已批准方案、交付策略",
		"workflow.auto_delivery.output": "提交、检查、PR/合并结果，或明确的阻塞原因",
		"workflow.auto_patch.feature": "自动修复",
		"workflow.auto_patch.mission": "接手 Jira Task/Bug，完成聚焦修复并安全交接。",
		"workflow.auto_patch.input": "符合条件的 Jira 卡片、仓库边界",
		"workflow.auto_patch.output": "修复证据、验证结果和 PR/直接推送结果",
		"workflow.manager.feature": "Manager",
		"workflow.manager.mission": "澄清意图、创建合适的工作项，并协调三个能力负责人。",
		"workflow.manager.input": "业务请求、待决策事项、Loop 状态",
		"workflow.manager.output": "一个问题、一张工作卡，或一项路由后的执行请求",
		"label.autoScan": "自动扫描",
		"label.autoDelivery": "自动交付",
		"label.autoPatch": "自动修复",
		"label.manager": "Manager",
		"label.entryPoint": "入口",
		"label.feishuEntry": "用户 / 飞书入口",
		"label.managerLayer": "协调层",
		"label.capabilityOwners": "能力负责人",
		"label.role": "角色",
		"label.input": "输入",
		"label.output": "输出",
		"label.owns": "负责",
		"label.receives": "接收",
		"label.returns": "产出",
		"label.gateway": "网关",
		"label.agentsReady": "就绪 Agent",
		"label.workflowsActive": "运行中工作流",
		"label.questionsWaiting": "待回答问题",
		"label.agentRoles": "Agent 角色",
		"label.recordedTurns": "已记录对话",
		"label.processedQuestions": "已处理问题",
		"label.averageDuration": "平均耗时",
		"label.needsAttention": "需要关注",
		"label.rolesSeen": "涉及角色",
		"label.businessReadyCapabilities": "三个真人负责的能力",
		"label.conversationClear": "对话清晰",
		"label.unanswered": "{{count}} 个未回答",
		"label.sharedRuntime": "{{count}} 个角色 · 共享运行时",
		"label.currentStory": "当前 Story",
		"label.status": "状态",
		"label.elapsed": "耗时",
		"label.finished": "结束时间",
		"label.jiraCard": "Jira 卡片",
		"label.branch": "分支",
		"label.repositories": "代码仓库",
		"label.started": "开始时间",
		"label.issues": "问题",
		"label.duration": "时长",
		"label.artifacts": "产物",
		"label.story": "Story",
		"label.pullRequests": "Pull Request",
		"label.checks": "检查",
		"label.operation": "操作",
		"label.finishedAt": "结束时间",
		"label.log": "日志",
		"label.summary": "摘要",
		"label.jira": "Jira",
		"label.trace": "Trace",
		"label.repository": "代码仓库",
		"label.localCommit": "本地提交",
		"label.roleId": "角色 ID",
		"label.workflow": "工作流",
		"label.prompt": "提示词",
		"label.conversation": "对话",
		"label.typingReaction": "输入反馈",
		"label.lookbackDays": "回溯天数",
		"label.cron": "五字段 Cron",
		"label.intervalMinutes": "间隔（分钟）",
		"label.eligibleStatuses": "符合条件的 Jira 状态",
		"label.moveStarted": "开始时流转到",
		"label.moveCompleted": "完成时流转到",
		"label.moveFailed": "失败时流转到",
		"label.moveBlocked": "阻塞时流转到",
		"label.outputLanguage": "输出语言",
		"label.languageGeneration": "生成语言",
		"label.spreadsheetTab": "表格页签名称",
		"label.spreadsheetToken": "表格 Token / URL",
		"label.cursorModel": "Cursor 模型",
		"label.softTimeout": "软超时（秒）",
		"label.hardTimeout": "硬超时（秒）",
		"label.maxJobs": "最大并发任务数",
		"label.soulVersion": "SOUL 版本",
		"label.feishuAppId": "飞书 App ID",
		"label.feishuAppSecret": "飞书 App Secret",
		"label.completed": "已完成",
		"label.openFindings": "开放问题",
		"label.successfulScan": "成功扫描 · 7 天",
		"label.failed7d": "失败 · 7 天",
		"label.lookbackWindow": "回溯窗口",
		"label.conversationAndActions": "对话和操作均可用",
		"label.conversationPaused": "对话已在设置中暂停",
		"label.credentialsRequired": "需要配置凭证",
		"label.requestResult": "请求 + 结果",
		"label.resultCaptured": "已记录结果 · 请求来自未记录转录的旧版本",
		"label.traceOnly": "仅 Trace",
		"label.executionTrail": "执行轨迹",
		"label.debugDetails": "调试详情",
		"label.promptNotCaptured": "当前运行时没有记录原始提示词。",
		"label.olderTrace": "这条旧 Trace 有结果，但当时的运行时没有记录收到的消息。",
		"label.noFinalResponse": "没有保留最终响应文本；如需更多证据，请打开 Agent 日志中的源 Trace。",
		"label.activityRetention": "这里只显示有边界的本地请求/结果文本。Trace ID 和原始执行证据仍保存在本地 Agent 存储中。",
		"label.high": "高",
		"label.medium": "中",
		"label.low": "低",
		"label.untitledFinding": "未命名问题",
		"label.unknownRepository": "未知代码仓库",
		"label.reasonOptional": "原因（可选）",
		"label.ignoreQuestion": "要将此问题标记为忽略吗？",
		"label.ignorePlaceholder": "为什么可以安全忽略？",
		"label.noSnippet": "此历史问题没有记录代码片段。",
		"label.notRecorded": "未记录。",
		"label.notStarted": "等待交付触发",
		"label.running": "运行中",
		"label.pending": "待处理",
		"label.stopped": "已停止",
		"label.needsAttentionState": "需要关注",
		"label.startedAt": "开始于 {{value}}",
		"label.finishedAtValue": "结束于 {{value}}",
		"label.requested": "请求",
		"label.result": "结果",
		"label.noLog": "没有记录日志内容。",
		"label.noSchedulerLog": "没有记录调度输出。",
		"label.noSummary": "没有记录摘要。",
		"label.recentRawOutput": "最近的原始输出",
		"label.close": "关闭",
		"label.checksPassed": "{{count}} 个通过",
		"label.checksFailed": "{{count}} 个失败",
		"label.checksSkipped": "{{count}} 个跳过",
		"label.verification": "验证",
		"label.checksTitle": "检查",
		"heading.managerOverview": "Manager 总览",
		"heading.agentActivity": "Agent 活动",
		"heading.conversationRecords": "对话记录",
		"heading.agentRoster": "Agent 阵容",
		"heading.agentTeam": "Agent 阵容与工作流",
		"heading.agentArchitecture": "Agent 架构",
		"heading.workflowControl": "工作流控制",
		"heading.questionsWaiting": "等待你的问题",
		"heading.scanHistory": "扫描历史",
		"heading.trackedFindings": "跟踪中的问题",
		"heading.currentProgress": "当前进度",
		"heading.deliveryHistory": "交付历史",
		"heading.schedulerActivity": "调度活动",
		"heading.patchHistory": "修复历史",
		"heading.stories": "Stories",
		"heading.workspaceSettings": "工作区设置",
		"heading.agentRoles": "Agent 角色",
		"heading.automationSchedules": "自动化调度",
		"heading.executionModels": "执行模型",
		"heading.publishPolicy": "发布策略",
		"heading.notifications": "通知",
		"heading.variableKeys": "变量密钥",
		"heading.testCases": "测试用例",
		"heading.workflow": "{{feature}} 工作流",
		"action.openSettings": "打开设置",
		"action.configureAgent": "配置 Agent",
		"action.manageCapture": "管理记录",
		"action.viewActivity": "查看活动",
		"action.inspect": "查看 {{feature}}",
		"action.startScan": "开始扫描",
		"action.runCycle": "运行一轮",
		"action.viewRawLog": "查看原始日志",
		"action.openLog": "打开失败日志",
		"action.markIgnored": "标记为忽略",
		"action.viewDetail": "查看详情",
		"action.hideDetail": "隐藏详情",
		"action.pullRequest": "Pull Request",
		"action.startDelivery": "开始交付",
		"action.saveChanges": "保存更改",
		"action.savePrompt": "保存提示词",
		"action.searchStories": "搜索 Story",
		"action.filterStories": "筛选 Story",
		"action.showingReadyStories": "正在显示业务就绪的 Story",
		"action.filterReadyStories": "筛选业务就绪的 Story",
		"action.exitFullscreen": "退出全屏",
		"action.viewFullscreen": "查看全屏",
		"action.start": "开始",
		"action.save": "保存",
		"action.runScan": "开始扫描吗？",
		"action.confirmScan": "确认开始扫描",
		"action.scanBody": "这将为 {{project}} 启动自动扫描。",
		"action.scanConfirmBody": "确定现在为 {{project}} 启动扫描吗？扫描 Agent 将针对已配置的代码仓库运行。"
	},
	"zh-Hant": {
		"language.label": "語言",
		"language.en": "English",
		"language.zhHans": "簡體中文",
		"language.zhHant": "繁體中文",
		"nav.overview": "總覽",
		"nav.activity": "活動記錄",
		"nav.scan": "自動掃描",
		"nav.delivery": "自動交付",
		"nav.patch": "自動修復",
		"nav.observatory": "觀測台",
		"nav.repositories": "程式碼儲存庫",
		"nav.prompts": "工作流",
		"nav.settings": "設定",
		"context.overview.title": "管理者總覽",
		"context.overview.description": "查看 Agent 職責、工作流健康度和下一項需要人工決策的事項。",
		"context.activity.title": "Agent 活動",
		"context.activity.description": "查看對話記錄、處理結果以及每次 Agent 執行背後的證據。",
		"context.scan.title": "自動掃描",
		"context.scan.description": "查看掃描歷史並管理已追蹤的問題。",
		"context.delivery.title": "自動交付",
		"context.delivery.description": "查看 Story 執行、驗證和 Pull Request 交付。",
		"context.patch.title": "自動修復",
		"context.patch.description": "查看 Jira Task/Bug 擷取、聚焦修復和安全交接。",
		"context.observatory.title": "觀測台",
		"context.observatory.description": "瀏覽和編輯 Story 說明與技術方案。",
		"context.repositories.title": "程式碼儲存庫",
		"context.repositories.description": "管理本地儲存庫、自動化權限和交付驗證策略。",
		"context.prompts.title": "工作流",
		"context.prompts.description": "查看各項本地自動化背後的提示詞、腳本、控制點和恢復路徑。",
		"context.settings.title": "設定",
		"context.settings.description": "配置工作區、排程和本地整合。",
		"common.updated": "更新於 {{value}}",
		"common.syncing": "同步中…",
		"common.project": "專案",
		"common.currentProject": "目前專案",
		"common.openSettings": "開啟設定",
		"common.manageCapture": "管理記錄",
		"common.loadingWorkspace": "正在載入本地工作區狀態…",
		"common.expandNavigation": "展開導覽",
		"common.collapseNavigation": "收起導覽",
		"common.version": "版本 {{value}}",
		"common.staticReport": "靜態報告模式：互動操作不可用。",
		"common.unableLoadState": "無法載入 Dashboard 狀態",
		"common.requestFailed": "請求失敗",
		"common.unsavedSettings": "設定中有未儲存的變更，要不儲存就離開嗎？",
		"common.unsavedObservatory": "觀測台有未儲存的變更，要不儲存就離開嗎？",
		"common.noData": "暫無資料。",
		"common.cancel": "取消",
		"common.close": "關閉",
		"common.later": "稍後",
		"common.save": "儲存",
		"common.saving": "儲存中…",
		"common.confirm": "確認",
		"common.continue": "繼續",
		"common.start": "開始",
		"common.stop": "停止",
		"common.retry": "重試",
		"common.loading": "載入中…",
		"common.enabled": "已啟用",
		"common.paused": "已暫停",
		"common.active": "執行中",
		"common.off": "關閉",
		"common.all": "全部",
		"common.clear": "清除",
		"common.selected": "已選擇 {{count}} 項",
		"common.statusesSelected": "已選擇 {{count}} 個狀態",
		"common.previous": "上一頁",
		"common.next": "下一頁",
		"common.pageOf": "第 {{page}} 頁，共 {{count}} 頁",
		"common.showing": "顯示 {{count}} 項",
		"common.debugDetails": "除錯詳情",
		"common.originalPrompt": "傳送給 Agent 的原始提示詞",
		"common.records": "{{count}} 筆記錄",
		"common.runs": "{{count}} 次執行",
		"common.recentEvents": "最近 {{count}} 個事件",
		"common.yes": "是",
		"common.no": "否",
		"common.unknown": "未知",
		"common.workspace": "工作區",
		"common.agent": "Agent",
		"common.clarification": "釐清",
		"common.manager": "Manager",
		"common.you": "你",
		"common.trace": "Trace",
		"common.viewActivity": "查看活動",
		"common.viewLog": "查看日誌",
		"common.viewTrace": "查看 Trace",
		"common.open": "開啟",
		"common.inspect": "查看",
		"common.noAgentRoles": "暫無可用的 Agent 角色。",
		"common.noAgentQuestions": "沒有待回答的 Agent 問題。",
		"common.noConversationRecords": "沒有符合篩選條件的對話記錄。",
		"common.noFindings": "沒有符合該狀態的問題。",
		"common.noStoriesFilter": "沒有符合篩選條件的 Story。",
		"common.noStories": "文件儲存庫中沒有找到 Story。",
		"common.selectStory": "選擇一個 Story 查看。",
		"common.noAgentHistory": "暫無 Agent 對話儲存。閘道啟動後，新飛書對話會顯示在這裡。",
		"common.askAgents": "在飛書中詢問 Agent，然後重新整理此頁面。",
		"common.activityStoreFirstTurn": "首次 Agent 對話後會建立本地活動記錄。",
		"common.noDeliveryHistory": "暫無交付歷史。",
		"common.noPatchHistory": "暫無自動修復歷史。",
		"common.noDeliveryActivity": "暫無已記錄的定時交付活動。",
		"common.noPatchActivity": "暫無已記錄的自動修復活動。",
		"common.noAgentRolesSettings": "暫無可用的 Agent 角色。",
		"common.noIntegrationKeys": "未設定本地整合金鑰。",
		"common.valueFor": "{{name}} 的值",
		"common.revealValue": "顯示值",
		"common.copyValue": "複製值",
		"common.copyCode": "複製程式碼",
		"common.showFullscreen": "全螢幕顯示",
		"common.closeFullscreen": "關閉全螢幕",
		"common.zoomOut": "縮小",
		"common.resetView": "重設視圖",
		"common.zoomIn": "放大",
		"common.diagram": "圖表",
		"common.image": "圖片",
		"common.formattingTools": "格式工具",
		"common.documentBody": "文件正文",
		"common.add": "新增",
		"common.navigation": "Lumon 導航",
		"common.dashboardSections": "Dashboard 區段",
		"common.explainSetting": "解釋此設定",
		"common.originalMarkdown": "原始 Markdown",
		"common.preview": "預覽",
		"common.live": "即時",
		"common.attempt": "第 {{number}} 次：{{duration}}",
		"common.overwriting": "覆寫中…",
		"common.overwriteRemote": "覆寫遠端版本",
		"common.remoteDecision": "遠端更新需要你的決定",
		"common.remoteConflictCopy": "Lumon 已提交本地工作區變更，但遠端分支在推送前發生了變化。請先檢查遠端變更，再決定是否覆寫。",
		"common.onlyTaskBugCards": "這裡只顯示目前活躍 Sprint 中的 Task 和 Bug 卡片。",
		"common.noPendingPatchCards": "目前活躍 Sprint 中沒有待處理的 Auto Patch Jira 卡片。",
		"common.patchFlow": "捕獲 → 儲存庫 → 修復 → 發布",
		"common.retryDeliveryCopy": "這會移除 Story 工作樹，重置其 Delivery 和 Jira 狀態，然後啟動新一輪執行。失敗執行和日誌仍會保留在歷史紀錄中。",
		"common.repositoryGovernance": "儲存庫治理",
		"common.addRepository": "新增儲存庫",
		"common.repositoryIntro": "透過 Git URL 連接儲存庫。Lumon 會將其複製到 repos/，偵測執行環境和建置工具，然後讓你批准可以修改或發布程式碼的自動化能力。",
		"common.attentionNote": "「需要關注」表示存在未提交變更、分支落後遠端，或分支/同步發生分叉。",
		"common.repositoryConfiguration": "儲存庫設定",
		"common.unnamedRepository": "未命名儲存庫",
		"common.generic": "通用",
		"common.noBuildTool": "未偵測到建置工具",
		"common.identityConnection": "身分與連線",
		"common.identityConnectionHelp": "從本地偵測得到；只有預設分支是可編輯的連線設定。",
		"common.localPath": "本地路徑",
		"common.remote": "遠端位址",
		"common.gitStatus": "Git 狀態",
		"common.branchSync": "分支同步",
		"common.defaultBranch": "預設分支",
		"common.runtimeBuild": "執行環境與建置",
		"common.runtimeBuildHelp": "從儲存庫檔案中偵測得到。儲存庫發生變化前，這些值為唯讀。",
		"common.language": "語言",
		"common.java": "Java",
		"common.node": "Node",
		"common.buildTools": "建置工具",
		"common.notDetected": "未偵測到",
		"common.automationPermissions": "自動化權限",
		"common.frontendDeliveryDisabled": "前端交付在全域策略中保持關閉，無法在這裡啟用。",
		"common.autoScanFixes": "Auto Scan 修復",
		"common.autoScanFixesHelp": "允許高信心度的 Scan 修復及其設定的發布流程。",
		"common.deliveryPermission": "Auto Delivery",
		"common.deliveryPermissionHelp": "允許此儲存庫執行已批准的技術交付工作。",
		"common.patchPermission": "Auto Patch",
		"common.patchPermissionHelp": "允許針對 Jira 驅動的修復並發布。",
		"common.deliveryVerification": "交付驗證",
		"common.deliveryVerificationHelp": "選擇實作完成後 Lumon 應為此儲存庫執行哪些驗證。",
		"common.policy": "策略",
		"common.runVerification": "執行驗證",
		"common.runVerificationHelp": "使用自動設定或你自訂的指令。",
		"common.skipVerification": "跳過驗證",
		"common.skipVerificationHelp": "不執行編譯、靜態檢查或測試。",
		"common.executionSource": "執行來源",
		"common.automaticProfile": "自動設定",
		"common.automaticProfileHelp": "執行時從儲存庫檔案中偵測指令。",
		"common.customCommands": "自訂指令",
		"common.customCommandsHelp": "只執行下面輸入的指令。",
		"common.checksToRun": "要執行的檢查",
		"common.compileChecks": "編譯與靜態檢查",
		"common.compileChecksHelp": "編譯、語法、型別檢查、Lint 或 PMD 檢查。",
		"common.tests": "測試",
		"common.testsHelp": "單元測試、整合測試和測試套件指令。",
		"common.commands": "指令",
		"common.useSuggestedCommands": "使用 {{count}} 條建議指令{{suffix}}",
		"common.oneCommandPerLine": "每行一條指令。",
		"common.cloneUrl": "複製 URL",
		"common.cloneInspect": "複製並檢查",
		"common.addRepositoryDescription": "Lumon 會複製 Git URL、偵測分支和工具，啟用現有的 Scan 與 Delivery 行為，並預設授權 Auto Patch。",
		"common.settingsSections": "設定區段",
		"common.schedules": "排程",
		"common.agentConversations": "Agent 對話",
		"common.integrations": "整合",
		"common.configuredKeys": "個已設定金鑰",
		"settings.automation": "自動化",
		"settings.automationDescription": "決定工作何時可以推進的排程和執行策略。",
		"settings.agentTeam": "Agent 團隊",
		"settings.agentTeamDescription": "誰與人溝通、各角色負責什麼，以及哪些對話可以修改狀態。",
		"settings.projectOutput": "專案產出",
		"settings.projectOutputDescription": "Mark 和 Milchick 將請求轉成可測試 Story 時使用的預設設定。",
		"settings.runtime": "執行環境與整合",
		"settings.runtimeDescription": "模型選擇、發布行為、通知和本地金鑰值。",
		"settings.nextAgentTeam": "下一步：Agent 團隊",
		"settings.nextProjectOutput": "下一步：專案產出",
		"settings.nextRuntime": "下一步：執行環境與整合",
		"settings.backAutomation": "返回自動化",
		"settings.localConfiguration": "本地設定",
		"settings.controlPlane": "01 · 控制面",
		"settings.humanAgents": "02 · 面向人的 Agent",
		"settings.businessOutput": "03 · 業務產出",
		"settings.operatingDetails": "04 · 執行細節",
		"settings.globalFeishuAgents": "全域飛書 Agent",
		"settings.accessControl": "存取控制",
		"settings.accessControlDescription": "誰可以與 Agent 對話、誰可以修改狀態（解決問題、更新排程、啟動交付）。新增允許的群組聊天 ID 後，Dylan/Milchick 才能在被 @提及時回覆這些群組。",
		"settings.accessPerson": "使用者",
		"settings.accessChat": "群組聊天",
		"settings.selectPerson": "選擇使用者",
		"settings.selectChat": "選擇群組聊天",
		"settings.identityRoles": "此身分的存取權限",
		"settings.selectIdentityHelp": "選擇一個身分，然後編輯下方的三項存取權限。",
		"settings.canTalk": "可以與 Agent 對話",
		"settings.canMutate": "可以執行變更操作",
		"settings.canAdmin": "可以管理 Agent",
		"settings.accessSummary": "已設定身分",
		"settings.identityCount": "{{count}} 個身分記錄",
		"settings.rolesApplied": "項權限",
		"settings.agentCoreDescription": "這裡只編輯核心控制項。角色歸屬、安全邊界和 SOUL 檔案仍由 Agent 登錄表管理。",
		"settings.responsibility": "職責",
		"settings.legacyWarning": "舊版 allow 模式對本地 Agent 不安全。建議使用按 Agent 設定的 Access & Exposure，並將 default_policy 設為 deny。",
		"settings.recentPeople": "最近聯絡人",
		"settings.recentChats": "最近群組聊天",
		"settings.addMutationUser": "點擊新增為可變更使用者",
		"settings.allowChat": "點擊允許此聊天",
		"settings.noRecentPeople": "目前沒有最近的飛書聯絡人。先向 Dylan 或 Mark 傳送一則訊息，再重新整理設定。",
		"settings.generationLanguage": "生成語言",
		"settings.generationDescription": "控制 Mark 為此專案寫入飛書試算表的語言。mbpass 預設使用繁體中文。",
		"settings.afterGeneration": "修改語言或試算表後，請讓 Milchick/Mark 重新生成 Story，使新列使用選定的試算表。",
		"settings.executionDescription": "選擇預設模型，或輸入自訂 Cursor 模型 ID。自訂值必須受 Cursor 支援；Lumon 不會驗證模型是否可用。",
		"settings.automationOutcome": "自動化結果",
		"settings.notificationsDescription": "控制 Scan 和 Delivery 是否向已設定的飛書 Webhook 發布卡片。Webhook URL 仍位於變數金鑰中。",
		"settings.storedWorkspace": "僅儲存在此工作區",
		"settings.availableKeys": "可用金鑰",
		"settings.availableKeysDescription": "顯示值以檢查，或直接輸入替換值。儲存時不會包含顯示引號。",
		"settings.revealReplacement": "顯示或輸入替換值",
		"settings.unsavedChanges": "有未儲存的變更",
		"settings.allSaved": "所有變更已儲存",
		"settings.deliveryPaused": "交付輪詢已暫停。",
		"settings.patchPaused": "Auto Patch 輪詢已暫停。",
		"settings.deliveryStatusHelp": "選擇所有可以啟動 Auto Delivery 的 Jira 狀態。Story 還必須處於 Business Ready、Technical Approved 且未在執行。",
		"settings.deliveryStatusNote": "選擇 To Do、Backlog、In Progress 或其他符合條件的 Jira 狀態。失敗時，Lumon 會將 Jira 卡片轉換到選定的 Block 狀態，並新增需要關注的評論。",
		"settings.patchStatusNote": "只捕獲 Task 和 Bug 卡片。阻塞卡片會在收到新的外部 Jira 評論後重試。",
		"settings.scanDefaultDescription": "尚未設定週期性掃描。",
		"settings.direct": "直接推送",
		"settings.merge": "合併",
		"settings.pullRequest": "PR",
		"settings.openPullRequest": "開啟 Pull Request",
		"settings.mergeAfterPullRequest": "在 Pull Request 後合併",
		"settings.pushDirectly": "直接推送到 main 分支",
		"settings.feishuNotifications": "飛書通知",
		"settings.allowedChatIds": "允許的群組聊天 ID",
		"settings.allowedUserIds": "允許的使用者 ID",
		"settings.mutationUserIds": "可變更使用者 ID",
		"settings.adminUserIds": "管理員使用者 ID",
		"settings.allowedChatHelp": "將群組聊天加入白名單。除非群組已列出，否則 Dylan/Milchick 只能私聊；在群組中仍必須 @提及。",
		"settings.allowedUserHelp": "為空表示所有使用者都可以詢問唯讀問題。",
		"settings.mutationUserHelp": "解決問題、更新排程和啟動交付時必需。為空時預設拒絕。",
		"settings.adminUserHelp": "管理員也可以執行變更操作。",
		"settings.appSecretRequired": "飛書客戶端登入必需。",
		"settings.keepSecret": "留空以保留目前金鑰",
		"settings.enterSecret": "輸入 App Secret",
		"settings.runtimeIdentityHelp": "執行環境身分由 Agent 登錄表管理。",
		"settings.workflowOwnershipHelp": "工作流歸屬由 Agent 登錄表管理。",
		"settings.publishDescription": "直接推送使用已設定的 Git 儲存庫憑證；PR 和合併使用 GitHub CLI。Auto Scan 保留 PR 審查閘門，不支援直接推送。",
		"settings.deploymentTracking": "部署狀態追蹤",
		"settings.deploymentTrackingDescription": "發布後追蹤已設定的 CI/CD 執行，只有部署真正完成後才回報結果。憑證保留在本機環境變數中。",
		"settings.deploymentProvider": "提供者",
		"settings.deploymentDisabled": "未啟用",
		"settings.jenkins": "Jenkins",
		"settings.githubActions": "GitHub Actions",
		"settings.pollInterval": "輪詢間隔（秒）",
		"settings.deploymentTimeout": "逾時（秒）",
		"settings.deploymentProviderHelp": "發布後要觀察哪個 CI/CD 系統的部署執行。",
		"settings.deploymentOwner": "追蹤負責人",
		"settings.deploymentOwnerValue": "Milchick · 工程營運經理",
		"settings.deploymentOwnerHelp": "Milchick 負責判斷後續歸屬：原始碼或交付失敗交給 Mark，Jira 修復交給 Irving，基礎設施或無法判斷的問題回報人工決策。",
		"settings.deploymentFailureHandling": "背景 worker 負責輪詢提供者；Milchick 接收最終證據並決定下一位負責人，不再把所有失敗硬編碼交給 Mark。",
		"settings.credentials": "憑證",
		"settings.configured": "已設定",
		"settings.notConfigured": "未設定",
		"settings.localGhLogin": "本機 gh 登入",
		"settings.jenkinsPipeline": "Jenkins 部署流水線",
		"settings.jenkinsPipelineHelp": "用於定位要觀察的 Jenkins 流水線。例如：folder/job-name。Lumon 不會用此欄位執行程式碼。",
		"settings.jenkinsCredentials": "請在變數金鑰中設定 JENKINS_URL 和 JENKINS_AUTH。值保留在工作區環境中，不會寫入 delivery.json。",
		"settings.githubCredentials": "GitHub Actions 使用工作區執行器的本機 gh 登入狀態。這裡不輸入也不儲存 Token。",
		"settings.githubRepository": "GitHub 儲存庫",
		"settings.githubWorkflow": "Workflow（可選）",
		"label.deployment": "部署",
		"label.provider": "提供者",
		"label.lastChecked": "上次檢查",
		"action.openDeployment": "開啟部署",
		"editor.heading": "標題",
		"editor.editLink": "編輯連結 URL",
		"editor.linkUrl": "連結 URL",
		"editor.bold": "粗體",
		"editor.italic": "斜體",
		"editor.link": "連結 — Shift+點擊連結可定位游標，然後編輯",
		"editor.list": "清單",
		"editor.code": "程式碼",
		"prompt.original": "原始 Markdown",
		"prompt.preview": "預覽",
		"customModel.enter": "輸入自訂 Cursor 模型",
		"customModel.id": "Cursor 模型 ID",
		"customModel.placeholder": "例如：cursor-grok-4.5-medium",
		"customModel.copy": "Lumon 不會驗證模型是否可用，該值將在下一次執行時使用。",
		"customModel.edit": "編輯自訂模型",
		"customModel.option": "自訂 Cursor 模型 ID…",
		"customModel.badge": "自訂",
		"customModel.help": "使用 Cursor 支援的模型 ID。",
		"status.completed": "已完成",
		"status.passed": "通過",
		"status.failed": "失敗",
		"status.skipped": "已略過",
		"status.open": "開放",
		"status.inProgress": "進行中",
		"status.awaitingDeploy": "等待部署",
		"status.running": "執行中",
		"status.active": "使用中",
		"status.notSet": "未設定",
		"status.notConfigured": "未設定",
		"status.resolved": "已解決",
		"status.reopened": "已重新開啟",
		"status.synced": "已同步",
		"status.ignored": "已忽略",
		"status.blocked": "已阻塞",
		"status.pending": "待處理",
		"status.prOpen": "PR 已開啟",
		"status.notStarted": "未開始",
		"status.devDone": "開發完成",
		"status.approved": "已核准",
		"status.ready": "就緒",
		"status.draft": "草稿",
		"status.done": "完成",
		"status.clarifying": "釐清中",
		"status.changed": "已變更",
		"label.business": "業務",
		"label.technical": "技術",
		"workflow.auto_scan.feature": "自動掃描",
		"workflow.auto_scan.mission": "發現反覆出現的工程風險，並整理成可供評審的證據。",
		"workflow.auto_scan.input": "程式碼儲存庫、掃描視窗、風險訊號",
		"workflow.auto_scan.output": "問題、嚴重程度、連結和後續問題",
		"workflow.auto_delivery.feature": "自動交付",
		"workflow.auto_delivery.mission": "推動已核准的 Story 完成實作、驗證和交付。",
		"workflow.auto_delivery.input": "就緒 Story、已核准方案、交付策略",
		"workflow.auto_delivery.output": "提交、檢查、PR/合併結果，或明確的阻塞原因",
		"workflow.auto_patch.feature": "自動修復",
		"workflow.auto_patch.mission": "接手 Jira Task/Bug，完成聚焦修復並安全交接。",
		"workflow.auto_patch.input": "符合條件的 Jira 卡片、儲存庫邊界",
		"workflow.auto_patch.output": "修復證據、驗證結果和 PR/直接推送結果",
		"workflow.manager.feature": "Manager",
		"workflow.manager.mission": "釐清意圖、建立合適的工作項目，並協調三個能力負責人。",
		"workflow.manager.input": "業務請求、待決策事項、Loop 狀態",
		"workflow.manager.output": "一個問題、一張工作卡，或一項路由後的執行請求",
		"label.autoScan": "自動掃描",
		"label.autoDelivery": "自動交付",
		"label.autoPatch": "自動修復",
		"label.manager": "Manager",
		"label.entryPoint": "入口",
		"label.feishuEntry": "使用者 / 飛書入口",
		"label.managerLayer": "協調層",
		"label.capabilityOwners": "能力負責人",
		"label.role": "角色",
		"label.input": "輸入",
		"label.output": "輸出",
		"label.owns": "負責",
		"label.receives": "接收",
		"label.returns": "產出",
		"label.gateway": "閘道",
		"label.agentsReady": "就緒 Agent",
		"label.workflowsActive": "執行中工作流",
		"label.questionsWaiting": "待回答問題",
		"label.agentRoles": "Agent 角色",
		"label.recordedTurns": "已記錄對話",
		"label.processedQuestions": "已處理問題",
		"label.averageDuration": "平均耗時",
		"label.needsAttention": "需要關注",
		"label.rolesSeen": "涉及角色",
		"label.businessReadyCapabilities": "三個真人負責的能力",
		"label.conversationClear": "對話清晰",
		"label.unanswered": "{{count}} 個未回答",
		"label.sharedRuntime": "{{count}} 個角色 · 共用執行時",
		"label.currentStory": "目前 Story",
		"label.status": "狀態",
		"label.elapsed": "耗時",
		"label.finished": "結束時間",
		"label.jiraCard": "Jira 卡片",
		"label.branch": "分支",
		"label.repositories": "程式碼儲存庫",
		"label.started": "開始時間",
		"label.issues": "問題",
		"label.duration": "時長",
		"label.artifacts": "產物",
		"label.story": "Story",
		"label.pullRequests": "Pull Request",
		"label.checks": "檢查",
		"label.operation": "操作",
		"label.finishedAt": "結束時間",
		"label.log": "日誌",
		"label.summary": "摘要",
		"label.jira": "Jira",
		"label.trace": "Trace",
		"label.repository": "程式碼儲存庫",
		"label.localCommit": "本地提交",
		"label.roleId": "角色 ID",
		"label.workflow": "工作流",
		"label.prompt": "提示詞",
		"label.conversation": "對話",
		"label.typingReaction": "輸入回饋",
		"label.lookbackDays": "回溯天數",
		"label.cron": "五欄位 Cron",
		"label.intervalMinutes": "間隔（分鐘）",
		"label.eligibleStatuses": "符合條件的 Jira 狀態",
		"label.moveStarted": "開始時流轉到",
		"label.moveCompleted": "完成時流轉到",
		"label.moveFailed": "失敗時流轉到",
		"label.moveBlocked": "阻塞時流轉到",
		"label.outputLanguage": "輸出語言",
		"label.languageGeneration": "生成語言",
		"label.spreadsheetTab": "試算表分頁名稱",
		"label.spreadsheetToken": "試算表 Token / URL",
		"label.cursorModel": "Cursor 模型",
		"label.softTimeout": "軟逾時（秒）",
		"label.hardTimeout": "硬逾時（秒）",
		"label.maxJobs": "最大並行工作數",
		"label.soulVersion": "SOUL 版本",
		"label.feishuAppId": "飛書 App ID",
		"label.feishuAppSecret": "飛書 App Secret",
		"label.completed": "已完成",
		"label.openFindings": "開放問題",
		"label.successfulScan": "成功掃描 · 7 天",
		"label.failed7d": "失敗 · 7 天",
		"label.lookbackWindow": "回溯視窗",
		"label.conversationAndActions": "對話和操作均可用",
		"label.conversationPaused": "對話已在設定中暫停",
		"label.credentialsRequired": "需要設定憑證",
		"label.requestResult": "請求 + 結果",
		"label.resultCaptured": "已記錄結果 · 請求來自未記錄轉錄的舊版本",
		"label.traceOnly": "僅 Trace",
		"label.executionTrail": "執行軌跡",
		"label.debugDetails": "除錯詳情",
		"label.promptNotCaptured": "目前執行時沒有記錄原始提示詞。",
		"label.olderTrace": "這條舊 Trace 有結果，但當時的執行時沒有記錄收到的訊息。",
		"label.noFinalResponse": "沒有保留最終回應文字；如需更多證據，請開啟 Agent 日誌中的源 Trace。",
		"label.activityRetention": "這裡只顯示有邊界的本地請求/結果文字。Trace ID 和原始執行證據仍保存在本地 Agent 儲存中。",
		"label.high": "高",
		"label.medium": "中",
		"label.low": "低",
		"label.untitledFinding": "未命名問題",
		"label.unknownRepository": "未知程式碼儲存庫",
		"label.reasonOptional": "原因（可選）",
		"label.ignoreQuestion": "要將此問題標記為忽略嗎？",
		"label.ignorePlaceholder": "為什麼可以安全忽略？",
		"label.noSnippet": "此歷史問題沒有記錄程式碼片段。",
		"label.notRecorded": "未記錄。",
		"label.notStarted": "等待交付觸發",
		"label.running": "執行中",
		"label.pending": "待處理",
		"label.stopped": "已停止",
		"label.needsAttentionState": "需要關注",
		"label.startedAt": "開始於 {{value}}",
		"label.finishedAtValue": "結束於 {{value}}",
		"label.requested": "請求",
		"label.result": "結果",
		"label.noLog": "沒有記錄日誌內容。",
		"label.noSchedulerLog": "沒有記錄排程輸出。",
		"label.noSummary": "沒有記錄摘要。",
		"label.recentRawOutput": "最近的原始輸出",
		"label.close": "關閉",
		"label.checksPassed": "{{count}} 個通過",
		"label.checksFailed": "{{count}} 個失敗",
		"label.checksSkipped": "{{count}} 個略過",
		"label.verification": "驗證",
		"label.checksTitle": "檢查",
		"heading.managerOverview": "Manager 總覽",
		"heading.agentActivity": "Agent 活動",
		"heading.conversationRecords": "對話記錄",
		"heading.agentRoster": "Agent 陣容",
		"heading.agentTeam": "Agent 陣容與工作流",
		"heading.agentArchitecture": "Agent 架構",
		"heading.workflowControl": "工作流控制",
		"heading.questionsWaiting": "等待你的問題",
		"heading.scanHistory": "掃描歷史",
		"heading.trackedFindings": "追蹤中的問題",
		"heading.currentProgress": "目前進度",
		"heading.deliveryHistory": "交付歷史",
		"heading.schedulerActivity": "排程活動",
		"heading.patchHistory": "修復歷史",
		"heading.stories": "Stories",
		"heading.workspaceSettings": "工作區設定",
		"heading.agentRoles": "Agent 角色",
		"heading.automationSchedules": "自動化排程",
		"heading.executionModels": "執行模型",
		"heading.publishPolicy": "發布策略",
		"heading.notifications": "通知",
		"heading.variableKeys": "變數金鑰",
		"heading.testCases": "測試案例",
		"heading.workflow": "{{feature}} 工作流",
		"action.openSettings": "開啟設定",
		"action.configureAgent": "設定 Agent",
		"action.manageCapture": "管理記錄",
		"action.viewActivity": "查看活動",
		"action.inspect": "查看 {{feature}}",
		"action.startScan": "開始掃描",
		"action.runCycle": "執行一輪",
		"action.viewRawLog": "查看原始日誌",
		"action.openLog": "開啟失敗日誌",
		"action.markIgnored": "標記為忽略",
		"action.viewDetail": "查看詳情",
		"action.hideDetail": "隱藏詳情",
		"action.pullRequest": "Pull Request",
		"action.startDelivery": "開始交付",
		"action.saveChanges": "儲存變更",
		"action.savePrompt": "儲存提示詞",
		"action.searchStories": "搜尋 Story",
		"action.filterStories": "篩選 Story",
		"action.showingReadyStories": "正在顯示業務就緒的 Story",
		"action.filterReadyStories": "篩選業務就緒的 Story",
		"action.exitFullscreen": "退出全螢幕",
		"action.viewFullscreen": "查看全螢幕",
		"action.start": "開始",
		"action.save": "儲存",
		"action.runScan": "開始掃描嗎？",
		"action.confirmScan": "確認開始掃描",
		"action.scanBody": "這將為 {{project}} 啟動自動掃描。",
		"action.scanConfirmBody": "確定現在為 {{project}} 啟動掃描嗎？掃描 Agent 將針對已設定的程式碼儲存庫執行。"
	}
}, Fg = "en", Ig = (0, I.createContext)(null);
function Lg(e, t = {}) {
	return e.replace(/{{(\w+)}}/g, (e, n) => String(t[n] ?? ""));
}
function Rg(e, t, n) {
	return Lg(Pg[e][t] ?? Pg.en[t] ?? t, n);
}
function Z() {
	let e = (0, I.useContext)(Ig);
	if (!e) throw Error("DashboardI18nContext is missing");
	return e;
}
function zg({ children: e }) {
	let [t, n] = (0, I.useState)(() => {
		let e = window.localStorage.getItem(jg) || window.localStorage.getItem(Mg);
		return Ng.some((t) => t.value === e) ? e : "en";
	});
	Fg = t;
	let r = (e) => {
		Fg = e, n(e), window.localStorage.setItem(jg, e);
	}, i = (0, I.useCallback)((e, n) => Rg(t, e, n), [t]);
	return (0, I.useEffect)(() => {
		document.documentElement.lang = t === "zh-Hans" ? "zh-CN" : t === "zh-Hant" ? "zh-TW" : "en";
	}, [t]), /* @__PURE__ */ (0, J.jsx)(Ig.Provider, {
		value: {
			locale: t,
			setLocale: r,
			t: i
		},
		children: e
	});
}
var Bg = [
	{
		id: "overview",
		labelKey: "nav.overview",
		icon: tg
	},
	{
		id: "activity",
		labelKey: "nav.activity",
		icon: Fh
	},
	{
		id: "scan",
		labelKey: "nav.scan",
		icon: dg
	},
	{
		id: "delivery",
		labelKey: "nav.delivery",
		icon: vg
	},
	{
		id: "patch",
		labelKey: "nav.patch",
		icon: Gh
	},
	{
		id: "observatory",
		labelKey: "nav.observatory",
		icon: Yh
	},
	{
		id: "repositories",
		labelKey: "nav.repositories",
		icon: Zh
	},
	{
		id: "prompts",
		labelKey: "nav.prompts",
		icon: bg
	},
	{
		id: "settings",
		labelKey: "nav.settings",
		icon: pg
	}
], Vg = {
	overview: {
		titleKey: "context.overview.title",
		descriptionKey: "context.overview.description"
	},
	activity: {
		titleKey: "context.activity.title",
		descriptionKey: "context.activity.description"
	},
	scan: {
		titleKey: "context.scan.title",
		descriptionKey: "context.scan.description"
	},
	delivery: {
		titleKey: "context.delivery.title",
		descriptionKey: "context.delivery.description"
	},
	patch: {
		titleKey: "context.patch.title",
		descriptionKey: "context.patch.description"
	},
	observatory: {
		titleKey: "context.observatory.title",
		descriptionKey: "context.observatory.description"
	},
	repositories: {
		titleKey: "context.repositories.title",
		descriptionKey: "context.repositories.description"
	},
	prompts: {
		titleKey: "context.prompts.title",
		descriptionKey: "context.prompts.description"
	},
	settings: {
		titleKey: "context.settings.title",
		descriptionKey: "context.settings.description"
	}
}, Hg = [
	{
		workflow: "auto_scan",
		tab: "scan",
		feature: "Auto Scan",
		agent: "Dylan",
		mission: "Find recurring engineering risk and turn it into review-ready evidence.",
		input: "Repositories, scan window, risk signals",
		output: "Findings, severity, links, and next questions"
	},
	{
		workflow: "auto_delivery",
		tab: "delivery",
		feature: "Auto Delivery",
		agent: "Mark",
		mission: "Move an approved Story through implementation, verification, and delivery.",
		input: "Ready Story, approved plan, delivery policy",
		output: "Commits, checks, PR/merge result, or a clear blocker"
	},
	{
		workflow: "auto_patch",
		tab: "patch",
		feature: "Auto Patch",
		agent: "Irving",
		mission: "Pick up Jira Task/Bug work, apply a focused fix, and hand it off safely.",
		input: "Eligible Jira card, repository guardrails",
		output: "Patch evidence, verification, and PR/direct-push result"
	}
], Ug = {
	workflow: "manager",
	feature: "Manager",
	agent: "Milchick",
	mission: "Clarify intent, create the right work item, and coordinate the three capability owners.",
	input: "Business request, missing decisions, loop state",
	output: "A question, a work card, or a routed execution request"
};
function Wg(e) {
	return Hg.find((t) => t.workflow === e) || (e === "manager" ? Ug : null);
}
var Gg = {
	dylan: "assets/avatars/dylan.png",
	mark: "assets/avatars/mark.png",
	irving: "assets/avatars/irving.png",
	milchick: "assets/avatars/milchick.png"
}, Kg = {
	auto_scan: "dylan",
	auto_delivery: "mark",
	auto_patch: "irving",
	manager: "milchick"
};
function qg({ agentId: e, displayName: t, size: n }) {
	let r = String(e || "").trim().toLowerCase(), i = Gg[r];
	if (i) return /* @__PURE__ */ (0, J.jsx)("img", {
		className: `agent-avatar agent-avatar-${n}`,
		src: i,
		alt: "",
		"aria-hidden": "true"
	});
	let a = String(t || e || "A").trim().slice(0, 1).toUpperCase();
	return /* @__PURE__ */ (0, J.jsx)("span", {
		className: `activity-avatar activity-avatar-${r || "agent"}`,
		"aria-hidden": "true",
		children: a
	});
}
function Jg(e, t) {
	return {
		...e,
		feature: t(`workflow.${e.workflow}.feature`),
		mission: t(`workflow.${e.workflow}.mission`),
		input: t(`workflow.${e.workflow}.input`),
		output: t(`workflow.${e.workflow}.output`)
	};
}
var Yg = [
	{
		label: "Auto",
		value: "auto"
	},
	{
		label: "Composer 2.5",
		value: "composer-2.5"
	},
	{
		label: "Cursor Grok 4.5 Medium",
		value: "cursor-grok-4.5-medium"
	},
	{
		label: "Sonnet 4.5",
		value: "sonnet-4.5"
	},
	{
		label: "GPT-5.1 Codex",
		value: "gpt-5.1-codex"
	}
], Xg = "__custom__";
function Q(e, t = "—") {
	return e == null || e === "" ? t : String(e);
}
function Zg(e, t = "cursor-grok-4.5-medium") {
	return String(e ?? "").trim() || t;
}
function Qg(e) {
	return String(e ?? "").trim();
}
function $g(e) {
	if (!e) return "—";
	let t = new Date(String(e)), n = Fg === "zh-Hans" ? "zh-CN" : Fg === "zh-Hant" ? "zh-TW" : void 0;
	return Number.isNaN(t.valueOf()) ? String(e) : new Intl.DateTimeFormat(n, {
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
		hourCycle: "h23"
	}).format(t);
}
function e_(e, t) {
	if (!e || !t) return "—";
	let n = Math.round((new Date(t).valueOf() - new Date(e).valueOf()) / 1e3);
	if (!Number.isFinite(n) || n < 0) return "—";
	let r = Math.floor(n / 60), i = String(n % 60).padStart(2, "0");
	return Fg === "en" ? `${r}m ${i}s` : `${r}分${i}秒`;
}
function t_(e) {
	if (e == null || e === "") return "—";
	let t = Number(e);
	if (!Number.isFinite(t)) return "—";
	if (t < 1e3) return Fg === "en" ? `${Math.round(t)}ms` : `${Math.round(t)}毫秒`;
	let n = Math.round(t / 1e3), r = Math.floor(n / 60), i = String(n % 60).padStart(2, "0");
	return Fg === "en" ? `${r}m ${i}s` : `${r}分${i}秒`;
}
function n_(e) {
	let t = String(e || "unknown").toLowerCase().replaceAll("_", " ");
	return t === "open" || t === "reopened" || /(failed|blocked)/.test(t) ? "danger" : /(completed|succeeded|clean|passed|resolved|synced|configured|included|available|approved|ready|done|pr open)/.test(t) ? "success" : /(progress|running|active|partial|draft|not started|awaiting deployment)/.test(t) ? "info" : "neutral";
}
function r_(e) {
	let t = Q(e, "unknown").toLowerCase().replaceAll("_", " "), n = {
		"completed with findings": "status.completed",
		completed: "status.completed",
		clean: "status.completed",
		passed: "status.passed",
		failed: "status.failed",
		skipped: "status.skipped",
		open: "status.open",
		"in progress": "status.inProgress",
		"awaiting deploy": "status.awaitingDeploy",
		running: "status.running",
		configured: "status.active",
		"not configured": "status.notConfigured",
		setup: "status.notConfigured",
		resolved: "status.resolved",
		reopened: "status.reopened",
		synced: "status.synced",
		ignored: "status.ignored",
		blocked: "status.blocked",
		pending: "status.pending",
		active: "status.active",
		"pr open": "status.prOpen",
		"not started": "status.notStarted",
		"dev done": "status.devDone",
		approved: "status.approved",
		ready: "status.ready",
		draft: "status.draft",
		done: "status.done",
		clarifying: "status.clarifying",
		changed: "status.changed"
	};
	return n[t] ? Rg(Fg, n[t]) : t.replace(/\b\w/g, (e) => e.toUpperCase());
}
async function i_(e, t, n = {}) {
	let r = new URL(e, window.location.origin);
	(!n.method || n.method === "GET") && r.searchParams.set("project", t);
	let i = new Headers(n.headers), a = n.body;
	n.json && (i.set("Content-Type", "application/json"), a = JSON.stringify({
		...n.json,
		project: t
	}));
	let o = await fetch(r, {
		...n,
		headers: i,
		body: a
	}), s = await o.json();
	if (!o.ok) throw Error(s.error || "Request failed");
	return s;
}
function a_({ value: e }) {
	return /* @__PURE__ */ (0, J.jsx)("span", {
		className: `badge ${n_(e)}`,
		children: r_(e)
	});
}
function o_({ business: e, technical: t, compact: n = !1 }) {
	let { t: r } = Z();
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: `observatory-meta${n ? " compact" : ""}`,
		children: [/* @__PURE__ */ (0, J.jsxs)("span", {
			className: "observatory-meta-item",
			children: [/* @__PURE__ */ (0, J.jsx)("em", { children: r("label.business") }), /* @__PURE__ */ (0, J.jsx)(a_, { value: e || "draft" })]
		}), /* @__PURE__ */ (0, J.jsxs)("span", {
			className: "observatory-meta-item",
			children: [/* @__PURE__ */ (0, J.jsx)("em", { children: r("label.technical") }), /* @__PURE__ */ (0, J.jsx)(a_, { value: t || "draft" })]
		})]
	});
}
function s_(e) {
	let t = String(e || "").trim().slice(0, 10);
	return /^\d{4}-\d{2}-\d{2}$/.test(t) ? t : "";
}
function c_({ date: e, assignee: t }) {
	let n = s_(e), r = String(t || "").trim();
	return !n && !r ? null : /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "observatory-story-meta",
		children: [n ? /* @__PURE__ */ (0, J.jsxs)("span", {
			className: "observatory-story-meta-item",
			children: [/* @__PURE__ */ (0, J.jsx)(Lh, {
				size: 11,
				"aria-hidden": "true"
			}), n]
		}) : null, r ? /* @__PURE__ */ (0, J.jsxs)("span", {
			className: "observatory-story-meta-item",
			children: [/* @__PURE__ */ (0, J.jsx)(yg, {
				size: 11,
				"aria-hidden": "true"
			}), r]
		}) : null]
	});
}
function l_({ business: e, technical: t }) {
	let { t: n } = Z(), r = n_(e || "draft"), i = n_(t || "draft"), a = (e) => e === "success" ? /* @__PURE__ */ (0, J.jsx)("i", { className: "observatory-status-dot" }) : /* @__PURE__ */ (0, J.jsx)(Uh, { size: 11 });
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "observatory-story-status",
		children: [/* @__PURE__ */ (0, J.jsxs)("span", {
			className: `observatory-story-status-item ${r}`,
			children: [
				a(r),
				n("label.business"),
				" ",
				r_(e || "draft")
			]
		}), /* @__PURE__ */ (0, J.jsxs)("span", {
			className: `observatory-story-status-item ${i}`,
			children: [
				a(i),
				n("label.technical"),
				" ",
				r_(t || "draft")
			]
		})]
	});
}
function u_({ label: e, onClose: t, children: n }) {
	let { t: r } = Z(), [i, a] = (0, I.useState)(1), [o, s] = (0, I.useState)({
		x: 0,
		y: 0
	}), [c, l] = (0, I.useState)(!1), u = (0, I.useRef)(null), d = (e) => Math.min(kg, Math.max(Og, Number(e.toFixed(2)))), f = () => {
		a(1), s({
			x: 0,
			y: 0
		});
	};
	(0, I.useEffect)(() => {
		let e = (e) => {
			e.key === "Escape" && t(), (e.key === "+" || e.key === "=") && a((e) => d(e + Ag)), (e.key === "-" || e.key === "_") && a((e) => d(e - Ag)), e.key === "0" && f();
		};
		return window.addEventListener("keydown", e), () => window.removeEventListener("keydown", e);
	}, [t]);
	let p = (e) => {
		e.button === 0 && (u.current = {
			x: e.clientX,
			y: e.clientY
		}, l(!0), e.currentTarget.setPointerCapture(e.pointerId));
	}, m = (e) => {
		let t = u.current;
		if (!t) return;
		let n = e.clientX - t.x, r = e.clientY - t.y;
		u.current = {
			x: e.clientX,
			y: e.clientY
		}, s((e) => ({
			x: e.x + n,
			y: e.y + r
		}));
	}, h = (e) => {
		u.current = null, l(!1), e.currentTarget.hasPointerCapture(e.pointerId) && e.currentTarget.releasePointerCapture(e.pointerId);
	};
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "media-fullscreen",
		role: "dialog",
		"aria-modal": "true",
		"aria-label": e,
		children: [/* @__PURE__ */ (0, J.jsxs)("header", { children: [/* @__PURE__ */ (0, J.jsx)("span", { children: e }), /* @__PURE__ */ (0, J.jsxs)("div", {
			className: "media-fullscreen-actions",
			children: [
				/* @__PURE__ */ (0, J.jsx)("button", {
					type: "button",
					className: "button secondary",
					title: r("common.zoomOut"),
					"aria-label": r("common.zoomOut"),
					onClick: () => a((e) => d(e - Ag)),
					children: /* @__PURE__ */ (0, J.jsx)(Cg, { size: 14 })
				}),
				/* @__PURE__ */ (0, J.jsxs)("button", {
					type: "button",
					className: "button secondary media-fullscreen-zoom-label",
					title: r("common.resetView"),
					"aria-label": r("common.resetView"),
					onClick: f,
					children: [Math.round(i * 100), "%"]
				}),
				/* @__PURE__ */ (0, J.jsx)("button", {
					type: "button",
					className: "button secondary",
					title: r("common.zoomIn"),
					"aria-label": r("common.zoomIn"),
					onClick: () => a((e) => d(e + Ag)),
					children: /* @__PURE__ */ (0, J.jsx)(Sg, { size: 14 })
				}),
				/* @__PURE__ */ (0, J.jsx)("button", {
					type: "button",
					className: "button secondary",
					onClick: t,
					"aria-label": r("common.closeFullscreen"),
					children: /* @__PURE__ */ (0, J.jsx)(xg, { size: 14 })
				})
			]
		})] }), /* @__PURE__ */ (0, J.jsx)("div", {
			className: `media-fullscreen-stage${c ? " is-dragging" : ""}`,
			onPointerDown: p,
			onPointerMove: m,
			onPointerUp: h,
			onPointerCancel: h,
			children: /* @__PURE__ */ (0, J.jsx)("div", {
				className: "media-fullscreen-canvas",
				style: { transform: `translate(${o.x}px, ${o.y}px) scale(${i})` },
				children: n
			})
		})]
	});
}
async function d_(e) {
	let t = Tg.get(e);
	if (t) return t;
	let n = `mmd-${++Dg}`, { svg: r } = await Yi.render(n, e);
	return Tg.set(e, r), r;
}
var f_ = (0, I.memo)(function({ chart: e }) {
	let { t } = Z(), n = (0, I.useRef)(null), [r, i] = (0, I.useState)(!1);
	return (0, I.useEffect)(() => {
		let t = n.current;
		if (!t) return;
		let r = Tg.get(e);
		if (r) {
			t.innerHTML = r;
			return;
		}
		let i = !1;
		return d_(e).then((e) => {
			!i && n.current && (n.current.innerHTML = e);
		}).catch((e) => {
			!i && n.current && (n.current.innerHTML = `<pre class="mermaid-error">${String(e)}</pre>`);
		}), () => {
			i = !0;
		};
	}, [e]), /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [/* @__PURE__ */ (0, J.jsxs)("div", {
		className: "mermaid-wrap",
		children: [/* @__PURE__ */ (0, J.jsx)("button", {
			type: "button",
			className: "mermaid-fullscreen-btn",
			title: t("common.showFullscreen"),
			"aria-label": t("common.showFullscreen"),
			onClick: () => i(!0),
			children: /* @__PURE__ */ (0, J.jsx)(og, { size: 14 })
		}), /* @__PURE__ */ (0, J.jsx)("div", {
			className: "mermaid-block",
			ref: n
		})]
	}), r && /* @__PURE__ */ (0, J.jsx)(u_, {
		label: t("common.diagram"),
		onClose: () => i(!1),
		children: /* @__PURE__ */ (0, J.jsx)("div", {
			className: "mermaid-block mermaid-block-fullscreen",
			dangerouslySetInnerHTML: { __html: Tg.get(e) || n.current?.innerHTML || "" }
		})
	})] });
});
function p_({ src: e, alt: t }) {
	let { t: n } = Z(), [r, i] = (0, I.useState)(!1);
	return e ? /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [/* @__PURE__ */ (0, J.jsxs)("span", {
		className: "markdown-image-wrap",
		children: [/* @__PURE__ */ (0, J.jsx)("button", {
			type: "button",
			className: "mermaid-fullscreen-btn",
			title: n("common.showFullscreen"),
			"aria-label": n("common.showFullscreen"),
			onClick: () => i(!0),
			children: /* @__PURE__ */ (0, J.jsx)(og, { size: 14 })
		}), /* @__PURE__ */ (0, J.jsx)("img", {
			src: e,
			alt: t || ""
		})]
	}), r && /* @__PURE__ */ (0, J.jsx)(u_, {
		label: t || n("common.image"),
		onClose: () => i(!1),
		children: /* @__PURE__ */ (0, J.jsx)("img", {
			src: e,
			alt: t || ""
		})
	})] }) : null;
}
function m_({ className: e, children: t }) {
	let { t: n } = Z(), r = String(t).replace(/\n$/, ""), [i, a] = (0, I.useState)(!1);
	return /language-mermaid/.test(e || "") ? /* @__PURE__ */ (0, J.jsx)(f_, { chart: r }) : !r.includes("\n") && !e ? /* @__PURE__ */ (0, J.jsx)("code", {
		className: e,
		children: t
	}) : /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "md-code-block",
		children: [/* @__PURE__ */ (0, J.jsxs)("div", {
			className: "md-code-toolbar",
			children: [/* @__PURE__ */ (0, J.jsx)("span", {
				className: "md-code-lang",
				children: (e || "").replace(/^language-/, "") || "code"
			}), /* @__PURE__ */ (0, J.jsx)("button", {
				type: "button",
				className: "md-code-copy",
				title: n("common.copyCode"),
				"aria-label": n("common.copyCode"),
				"data-copied": i ? "true" : void 0,
				onClick: () => {
					navigator.clipboard.writeText(r).then(() => {
						a(!0), window.setTimeout(() => a(!1), 1200);
					});
				},
				children: /* @__PURE__ */ (0, J.jsx)(Kh, { size: 14 })
			})]
		}), /* @__PURE__ */ (0, J.jsx)("pre", { children: /* @__PURE__ */ (0, J.jsx)("code", {
			className: e,
			children: r
		}) })]
	});
}
var h_ = {
	a({ href: e, children: t }) {
		return /* @__PURE__ */ (0, J.jsx)("a", {
			href: e,
			target: "_blank",
			rel: "noreferrer noopener",
			children: t
		});
	},
	img({ src: e, alt: t }) {
		return /* @__PURE__ */ (0, J.jsx)(p_, {
			src: e,
			alt: t
		});
	},
	code({ className: e, children: t }) {
		return /* @__PURE__ */ (0, J.jsx)(m_, {
			className: e,
			children: t
		});
	}
};
function g_({ content: e }) {
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "markdown-content",
		children: /* @__PURE__ */ (0, J.jsx)(Ed, {
			remarkPlugins: [jm],
			components: h_,
			children: e
		})
	});
}
function __(e) {
	let t = e.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
	return t ? {
		frontmatter: t[1],
		body: t[2]
	} : {
		frontmatter: "",
		body: e
	};
}
function v_(e, t) {
	return e ? `---\n${e}\n---\n${t.startsWith("\n") ? t : `\n${t}`}` : t;
}
var y_ = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"14\" height=\"14\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect width=\"14\" height=\"14\" x=\"8\" y=\"8\" rx=\"2\" ry=\"2\"/><path d=\"M4 16V4a2 2 0 0 1 2-2h12\"/></svg>";
function b_(e) {
	for (let t of Array.from(e.querySelectorAll("pre"))) {
		if (t.closest(".md-code-block, .mermaid-wrap") || t.classList.contains("mermaid-error")) continue;
		let e = t.querySelector("code"), n = ((e?.className || "").match(/language-([\w-]+)/) || [])[1] || "code", r = document.createElement("div");
		r.className = "md-code-block";
		let i = document.createElement("div");
		i.className = "md-code-toolbar", i.contentEditable = "false";
		let a = document.createElement("span");
		a.className = "md-code-lang", a.textContent = n;
		let o = document.createElement("button");
		o.type = "button", o.className = "md-code-copy", o.title = Rg(Fg, "common.copyCode"), o.setAttribute("aria-label", Rg(Fg, "common.copyCode")), o.innerHTML = y_, o.onclick = (n) => {
			n.preventDefault(), n.stopPropagation();
			let r = e?.textContent || t.textContent || "";
			navigator.clipboard.writeText(r).then(() => {
				o.dataset.copied = "true", window.setTimeout(() => {
					delete o.dataset.copied;
				}, 1200);
			});
		}, i.append(a, o), t.replaceWith(r), r.append(i, t);
	}
}
function x_(e) {
	let t = e.replace(/```mermaid\r?\n([\s\S]*?)```/g, (e, t) => {
		let n = `mm-${++Dg}`;
		Eg.set(n, t.trim());
		let r = Rg(Fg, "common.showFullscreen");
		return `\n\n<div class="mermaid-wrap" contenteditable="false" data-mm-id="${n}"><button type="button" class="mermaid-fullscreen-btn" data-mm-fullscreen title="${r}" aria-label="${r}"></button><div class="mermaid-block" data-mm-host></div></div>\n\n`;
	});
	return String(Jt.parse(t, { async: !1 }));
}
function S_() {
	let e = new bh({
		headingStyle: "atx",
		codeBlockStyle: "fenced",
		bulletListMarker: "-"
	});
	return e.addRule("fullscreenBtn", {
		filter: (e) => e instanceof HTMLElement && e.classList.contains("mermaid-fullscreen-btn"),
		replacement: () => ""
	}), e.addRule("codeToolbar", {
		filter: (e) => e instanceof HTMLElement && e.classList.contains("md-code-toolbar"),
		replacement: () => ""
	}), e.addRule("codeBlockShell", {
		filter: (e) => e instanceof HTMLElement && e.classList.contains("md-code-block"),
		replacement: (e, t) => {
			let n = t.querySelector("code"), r = t.querySelector("pre");
			return `\n\n\`\`\`${((n?.className || "").match(/language-([\w-]+)/) || [])[1] || ""}\n${(n?.textContent || r?.textContent || "").replace(/\n$/, "")}\n\`\`\`\n\n`;
		}
	}), e.addRule("mermaidIsland", {
		filter: (e) => e instanceof HTMLElement && e.classList.contains("mermaid-wrap") && !!e.getAttribute("data-mm-id"),
		replacement: (e, t) => {
			let n = t.getAttribute("data-mm-id") || "";
			return `\n\n\`\`\`mermaid\n${Eg.get(n) || ""}\n\`\`\`\n\n`;
		}
	}), e.addRule("imageWrap", {
		filter: (e) => e instanceof HTMLElement && e.classList.contains("markdown-image-wrap"),
		replacement: (e, t) => {
			let n = t.querySelector("img");
			return n ? `![${n.getAttribute("alt") || ""}](${n.getAttribute("src") || ""})` : "";
		}
	}), e;
}
async function C_(e) {
	let t = Array.from(e.querySelectorAll("[data-mm-host]"));
	await Promise.all(t.map(async (e) => {
		let t = e.closest(".mermaid-wrap")?.getAttribute("data-mm-id") || "", n = Eg.get(t);
		if (n) try {
			e.innerHTML = await d_(n);
		} catch (t) {
			e.innerHTML = `<pre class="mermaid-error">${String(t)}</pre>`;
		}
	}));
}
function w_(e, t, n) {
	return e && t !== n;
}
function T_(e) {
	let t = window.getSelection();
	if (!e || !t?.anchorNode) return null;
	let n = t.anchorNode, r = (n instanceof Element ? n : n.parentElement)?.closest("a");
	return !(r instanceof HTMLAnchorElement) || !e.contains(r) ? null : r;
}
function E_(e) {
	return !e.shiftKey && !e.metaKey && !e.altKey && (e.button === void 0 || e.button === 0);
}
function D_({ value: e, onChange: t }) {
	let { t: n } = Z(), { frontmatter: r, body: i } = __(e), a = (0, I.useRef)(null), o = (0, I.useRef)(!1), s = (0, I.useRef)(!1), c = (0, I.useRef)(i), l = (0, I.useRef)(S_()), [u, d] = (0, I.useState)(null), [f, p] = (0, I.useState)(!1);
	c.current = i;
	let m = (e) => t(v_(r, e)), h = () => {
		let e = a.current;
		if (!e) return;
		let t = l.current.turndown(e);
		w_(s.current, t, c.current) && m(t);
	}, g = (e) => {
		e.querySelectorAll("a[href]").forEach((e) => {
			e.setAttribute("target", "_blank"), e.setAttribute("rel", "noreferrer noopener");
		});
	}, _ = (0, I.useCallback)(async (e) => {
		let t = a.current;
		if (!t) return;
		s.current = !1, t.innerHTML = x_(e), b_(t), g(t);
		let r = "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"14\" height=\"14\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M15 3h6v6\"/><path d=\"m21 3-7 7\"/><path d=\"m3 21 7-7\"/><path d=\"M9 21H3v-6\"/></svg>";
		t.querySelectorAll("[data-mm-fullscreen]").forEach((e) => {
			e.innerHTML = r, e.onclick = (t) => {
				t.preventDefault(), t.stopPropagation();
				let n = e.parentElement?.querySelector("[data-mm-host]");
				d({
					kind: "html",
					value: n?.innerHTML || ""
				});
			};
		}), t.querySelectorAll("img").forEach((e) => {
			if (e.closest(".markdown-image-wrap")) return;
			let t = document.createElement("span");
			t.className = "markdown-image-wrap";
			let i = document.createElement("button");
			i.type = "button", i.className = "mermaid-fullscreen-btn", i.title = n("common.showFullscreen"), i.setAttribute("aria-label", n("common.showFullscreen")), i.innerHTML = r;
			let a = e.getAttribute("src") || "", o = e.getAttribute("alt") || "";
			i.onclick = (e) => {
				e.preventDefault(), e.stopPropagation(), d({
					kind: "img",
					value: a,
					alt: o
				});
			}, e.replaceWith(t), t.append(i, e);
		}), await C_(t);
	}, [n]);
	(0, I.useEffect)(() => {
		o.current || _(i);
	}, [i, _]), (0, I.useEffect)(() => {
		if (!f) return;
		let e = (e) => {
			e.key === "Escape" && p(!1);
		};
		return window.addEventListener("keydown", e), () => window.removeEventListener("keydown", e);
	}, [f]);
	let v = (e, t) => {
		a.current?.focus(), document.execCommand(e, !1, t), s.current = !0, h(), a.current && g(a.current);
	};
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: `observatory-doc${f ? " observatory-doc-fullscreen" : ""}`,
		children: [
			/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "observatory-toolbar",
				role: "toolbar",
				"aria-label": n("common.formattingTools"),
				children: [
					/* @__PURE__ */ (0, J.jsx)("button", {
						type: "button",
						title: n("editor.heading"),
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => v("formatBlock", "h2"),
						children: /* @__PURE__ */ (0, J.jsx)($h, { size: 14 })
					}),
					/* @__PURE__ */ (0, J.jsx)("button", {
						type: "button",
						title: n("editor.bold"),
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => v("bold"),
						children: /* @__PURE__ */ (0, J.jsx)(Ih, { size: 14 })
					}),
					/* @__PURE__ */ (0, J.jsx)("button", {
						type: "button",
						title: n("editor.italic"),
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => v("italic"),
						children: /* @__PURE__ */ (0, J.jsx)(eg, { size: 14 })
					}),
					/* @__PURE__ */ (0, J.jsx)("button", {
						type: "button",
						title: n("editor.link"),
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => {
							let e = a.current;
							e?.focus();
							let t = T_(e), r = t?.getAttribute("href") || "https://", i = window.prompt(n(t ? "editor.editLink" : "editor.linkUrl"), r);
							if (i === null) return;
							let o = i.trim();
							if (t) {
								if (!o) {
									v("unlink");
									return;
								}
								t.setAttribute("href", o), t.setAttribute("target", "_blank"), t.setAttribute("rel", "noreferrer noopener"), s.current = !0, h();
								return;
							}
							o && v("createLink", o);
						},
						children: /* @__PURE__ */ (0, J.jsx)(ng, { size: 14 })
					}),
					/* @__PURE__ */ (0, J.jsx)("button", {
						type: "button",
						title: n("editor.list"),
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => v("insertUnorderedList"),
						children: /* @__PURE__ */ (0, J.jsx)(ig, { size: 14 })
					}),
					/* @__PURE__ */ (0, J.jsx)("button", {
						type: "button",
						title: n("editor.code"),
						onMouseDown: (e) => e.preventDefault(),
						onClick: () => v("formatBlock", "pre"),
						children: /* @__PURE__ */ (0, J.jsx)(Gh, { size: 14 })
					})
				]
			}),
			/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "observatory-doc-preview-wrap",
				children: [/* @__PURE__ */ (0, J.jsx)("button", {
					type: "button",
					className: "observatory-doc-fullscreen-btn",
					title: n(f ? "common.closeFullscreen" : "common.showFullscreen"),
					"aria-label": n(f ? "common.closeFullscreen" : "common.showFullscreen"),
					onMouseDown: (e) => e.preventDefault(),
					onClick: () => p((e) => !e),
					children: f ? /* @__PURE__ */ (0, J.jsx)(sg, { size: 14 }) : /* @__PURE__ */ (0, J.jsx)(og, { size: 14 })
				}), /* @__PURE__ */ (0, J.jsx)("div", {
					ref: a,
					className: "observatory-doc-preview markdown-content",
					contentEditable: !0,
					suppressContentEditableWarning: !0,
					spellCheck: !1,
					role: "textbox",
					"aria-multiline": "true",
					"aria-label": n("common.documentBody"),
					onFocus: () => {
						o.current = !0;
					},
					onBlur: () => {
						o.current = !1, h();
					},
					onInput: () => {
						s.current = !0, h();
					},
					onClick: (e) => {
						let t = e.target;
						if (!t || t.closest("button")) return;
						let n = t.closest("a[href]");
						if (!(n instanceof HTMLAnchorElement) || !a.current?.contains(n) || !E_(e)) return;
						e.preventDefault(), e.stopPropagation();
						let r = n.getAttribute("href");
						r && window.open(r, "_blank", "noopener,noreferrer");
					}
				})]
			}),
			u && /* @__PURE__ */ (0, J.jsx)(u_, {
				label: u.kind === "img" ? u.alt || n("common.image") : n("common.diagram"),
				onClose: () => d(null),
				children: u.kind === "img" ? /* @__PURE__ */ (0, J.jsx)("img", {
					src: u.value,
					alt: u.alt || ""
				}) : /* @__PURE__ */ (0, J.jsx)("div", {
					className: "mermaid-block mermaid-block-fullscreen",
					dangerouslySetInnerHTML: { __html: u.value }
				})
			})
		]
	});
}
function O_({ label: e, children: t, onClick: n, danger: r = !1, disabled: i = !1, className: a = "" }) {
	return /* @__PURE__ */ (0, J.jsx)("button", {
		className: `icon-button ${r ? "danger" : ""} ${a}`,
		title: e,
		"aria-label": e,
		disabled: i,
		onClick: n,
		children: t
	});
}
function k_({ title: e, action: t, children: n, className: r = "" }) {
	return /* @__PURE__ */ (0, J.jsxs)("section", {
		className: `panel ${r}`,
		children: [/* @__PURE__ */ (0, J.jsxs)("header", {
			className: "panel-header",
			children: [/* @__PURE__ */ (0, J.jsx)("h3", { children: e }), t]
		}), n]
	});
}
function A_() {
	let { locale: e, setLocale: t, t: n } = Z(), [r, i] = (0, I.useState)(new URLSearchParams(window.location.search).get("project") || window.DASHBOARD_DATA?.interactive?.project || ""), [a, o] = (0, I.useState)(null), [s, c] = (0, I.useState)(Bg.find((e) => `/${e.id}` === window.location.pathname)?.id || "overview"), [l, u] = (0, I.useState)(""), [d, f] = (0, I.useState)(null), [p, m] = (0, I.useState)(!0), [h, g] = (0, I.useState)(() => window.localStorage.getItem("lumon-sidebar-collapsed") === "true" || window.localStorage.getItem("lumen-sidebar-collapsed") === "true"), [_, v] = (0, I.useState)(null), [y, b] = (0, I.useState)(!1), [x, S] = (0, I.useState)(!1), [C, w] = (0, I.useState)(null), T = (0, I.useRef)(0), E = (0, I.useRef)(!1), D = (0, I.useCallback)((e, t = "info") => f({
		message: e,
		tone: t
	}), []), O = async () => {
		let e = ++T.current;
		E.current || m(!0);
		try {
			let t = await i_("/api/state", r);
			if (e !== T.current) return;
			E.current = !0, o(t);
			let n = t.interactive?.workspace?.git_sync_conflict;
			w(n && typeof n == "object" && [
				"repo",
				"branch",
				"remote_oid",
				"local_oid"
			].every((e) => String(n[e] || "").trim()) ? n : null), v(/* @__PURE__ */ new Date()), !r && t.interactive?.project && i(t.interactive.project), u("");
		} catch (t) {
			if (e !== T.current) return;
			let r = window.DASHBOARD_DATA;
			r ? (E.current = !0, o(r), u(n("common.staticReport"))) : u(t instanceof Error ? t.message : n("common.unableLoadState"));
		} finally {
			e === T.current && m(!1);
		}
	};
	(0, I.useEffect)(() => {
		let e = !1, t = 0, n = !1, r = async () => {
			if (!(e || n)) {
				n = !0;
				try {
					await O();
				} finally {
					n = !1, e || (t = window.setTimeout(() => {
						r();
					}, 5e3));
				}
			}
		};
		return r(), () => {
			e = !0, window.clearTimeout(t);
		};
	}, [r]), (0, I.useEffect)(() => {
		if (!d) return;
		let e = window.setTimeout(() => f(null), 3200);
		return () => window.clearTimeout(e);
	}, [d]), (0, I.useEffect)(() => {
		window.localStorage.setItem("lumon-sidebar-collapsed", String(h));
	}, [h]), (0, I.useEffect)(() => {
		let e = () => c(Bg.find((e) => `/${e.id}` === window.location.pathname)?.id || "scan");
		return window.addEventListener("popstate", e), () => window.removeEventListener("popstate", e);
	}, []);
	let k = () => !(y && !window.confirm(n("common.unsavedSettings")) || x && !window.confirm(n("common.unsavedObservatory"))), ee = (e) => {
		if (e !== r && !k()) return;
		let t = new URL(window.location.href);
		t.searchParams.set("project", e), window.history.replaceState({}, "", `${window.location.pathname}${t.search}`), i(e), E.current = !1, b(!1), S(!1);
	}, A = (e) => {
		if (e !== s && !k()) return;
		let t = new URL(window.location.href);
		t.pathname = `/${e}`, window.history.pushState({}, "", t), c(e), e !== "settings" && b(!1), e !== "observatory" && S(!1);
	}, j = async (e, t, i) => {
		try {
			return await i_(e, r, {
				method: "POST",
				json: t
			}), D(i, "success"), O(), !0;
		} catch (e) {
			return D(e instanceof Error ? e.message : n("common.requestFailed"), "error"), !1;
		}
	}, M = a?.interactive?.projects || [], N = a?.product?.tagline || "Engineering, made legible.", P = Vg[s];
	return /* @__PURE__ */ (0, J.jsxs)("main", {
		className: `dashboard-layout ${h ? "sidebar-is-collapsed" : ""}`,
		children: [
			/* @__PURE__ */ (0, J.jsxs)("aside", {
				className: "sidebar",
				"aria-label": n("common.navigation"),
				children: [
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "sidebar-brand",
						children: [/* @__PURE__ */ (0, J.jsx)("img", {
							src: "assets/lumon-mark.png",
							className: "brand-mark",
							alt: "Lumon"
						}), /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "sidebar-brand-copy",
							children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: "Lumon" }), /* @__PURE__ */ (0, J.jsx)("span", { children: N })]
						})]
					}),
					/* @__PURE__ */ (0, J.jsx)("nav", {
						className: "side-nav",
						"aria-label": n("common.dashboardSections"),
						children: Bg.map((e) => {
							let t = e.icon, r = n(e.labelKey);
							return /* @__PURE__ */ (0, J.jsxs)("button", {
								title: r,
								className: s === e.id ? "active" : "",
								onClick: () => A(e.id),
								children: [/* @__PURE__ */ (0, J.jsx)(t, { size: 17 }), /* @__PURE__ */ (0, J.jsx)("span", { children: r })]
							}, e.id);
						})
					}),
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "sidebar-foot",
						children: [!h && /* @__PURE__ */ (0, J.jsx)("img", {
							src: "assets/inspire-group-logo.png",
							className: "company-mark",
							alt: "INSPIRE GROUP"
						}), /* @__PURE__ */ (0, J.jsx)("small", { children: h ? `V${wg}` : n("common.version", { value: wg }) })]
					})
				]
			}),
			/* @__PURE__ */ (0, J.jsx)("button", {
				type: "button",
				className: "icon-button sidebar-toggle",
				title: n(h ? "common.expandNavigation" : "common.collapseNavigation"),
				"aria-label": n(h ? "common.expandNavigation" : "common.collapseNavigation"),
				onPointerDown: (e) => {
					e.preventDefault(), e.stopPropagation(), g((e) => !e);
				},
				children: h ? /* @__PURE__ */ (0, J.jsx)(Bh, { size: 14 }) : /* @__PURE__ */ (0, J.jsx)(Rh, { size: 14 })
			}),
			/* @__PURE__ */ (0, J.jsxs)("section", {
				className: "content-area",
				children: [/* @__PURE__ */ (0, J.jsxs)("header", {
					className: "masthead",
					children: [/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "masthead-context",
						children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n(P.titleKey) }), /* @__PURE__ */ (0, J.jsx)("span", { children: n(P.descriptionKey) })]
					}), /* @__PURE__ */ (0, J.jsxs)("div", {
						className: "masthead-actions",
						children: [
							/* @__PURE__ */ (0, J.jsx)("span", {
								className: "last-updated",
								children: _ ? n("common.updated", { value: $g(_.toISOString()) }) : n("common.syncing")
							}),
							/* @__PURE__ */ (0, J.jsxs)("label", {
								className: "locale-picker",
								children: [/* @__PURE__ */ (0, J.jsx)("span", {
									className: "sr-only",
									children: n("language.label")
								}), /* @__PURE__ */ (0, J.jsx)("select", {
									"aria-label": n("language.label"),
									value: e,
									onChange: (e) => t(e.target.value),
									children: Ng.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
										value: e.value,
										children: e.value === "en" ? n("language.en") : e.value === "zh-Hans" ? n("language.zhHans") : n("language.zhHant")
									}, e.value))
								})]
							}),
							/* @__PURE__ */ (0, J.jsxs)("label", {
								className: "project-picker",
								children: [
									/* @__PURE__ */ (0, J.jsx)("span", { children: n("common.project") }),
									/* @__PURE__ */ (0, J.jsx)("select", {
										value: r,
										onChange: (e) => ee(e.target.value),
										children: M.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
											value: e.slug,
											children: e.name
										}, e.slug))
									}),
									/* @__PURE__ */ (0, J.jsx)(zh, { size: 15 })
								]
							})
						]
					})]
				}), /* @__PURE__ */ (0, J.jsxs)("div", {
					className: "page-content",
					children: [
						l && /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "status-note",
							children: [/* @__PURE__ */ (0, J.jsx)(Fh, { size: 15 }), l]
						}),
						!a && p ? /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "loading-state",
							children: [
								/* @__PURE__ */ (0, J.jsx)(ag, {
									size: 22,
									className: "spin"
								}),
								" ",
								n("common.loadingWorkspace")
							]
						}) : null,
						a && s === "overview" && /* @__PURE__ */ (0, J.jsx)(I_, {
							data: a,
							project: r,
							onNavigate: A
						}),
						a && s === "activity" && /* @__PURE__ */ (0, J.jsx)(L_, {
							data: a,
							project: r,
							onNavigate: A
						}),
						a && s === "scan" && /* @__PURE__ */ (0, J.jsx)(B_, {
							data: a,
							project: r,
							notify: D,
							reload: O
						}),
						a && s === "delivery" && /* @__PURE__ */ (0, J.jsx)(X_, {
							data: a,
							project: r,
							notify: D,
							reload: O
						}),
						a && s === "patch" && /* @__PURE__ */ (0, J.jsx)(Z_, {
							data: a,
							project: r,
							notify: D,
							reload: O
						}),
						a && s === "observatory" && /* @__PURE__ */ (0, J.jsx)(rv, {
							project: r,
							notify: D,
							onDirtyChange: S
						}),
						a && s === "repositories" && /* @__PURE__ */ (0, J.jsx)(xv, {
							data: a,
							interact: j
						}),
						a && s === "prompts" && /* @__PURE__ */ (0, J.jsx)(hv, {
							data: a,
							project: r,
							interact: j,
							notify: D
						}),
						a && s === "settings" && /* @__PURE__ */ (0, J.jsx)(Cv, {
							data: a,
							project: r,
							notify: D,
							onDirtyChange: b,
							reload: O
						})
					]
				}, s)]
			}),
			C && /* @__PURE__ */ (0, J.jsx)(j_, {
				conflict: C,
				project: r,
				notify: D,
				onClose: () => w(null),
				onResolved: O
			}),
			d && /* @__PURE__ */ (0, J.jsxs)("div", {
				className: `toast toast-${d.tone}`,
				role: "status",
				children: [d.tone === "success" ? /* @__PURE__ */ (0, J.jsx)(Hh, { size: 16 }) : d.tone === "error" ? /* @__PURE__ */ (0, J.jsx)(Vh, { size: 16 }) : /* @__PURE__ */ (0, J.jsx)(Uh, { size: 16 }), /* @__PURE__ */ (0, J.jsx)("span", { children: d.message })]
			})
		]
	});
}
function j_({ conflict: e, project: t, notify: n, onClose: r, onResolved: i }) {
	let { t: a } = Z(), [o, s] = (0, I.useState)(!1), [c, l] = (0, I.useState)(""), u = async () => {
		s(!0), l("");
		try {
			await i_("/api/git-sync/force", t, {
				method: "POST",
				json: {}
			}), n("Remote branch overwritten with the local Lumon commit", "success"), r(), await i();
		} catch (e) {
			let t = e instanceof Error ? e.message : "Unable to overwrite the remote branch";
			l(t);
		} finally {
			s(!1);
		}
	};
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal git-sync-conflict-modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": a("common.remoteDecision"),
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "modal-body compact",
				children: [
					/* @__PURE__ */ (0, J.jsx)("strong", { children: a("common.remoteDecision") }),
					/* @__PURE__ */ (0, J.jsx)("p", {
						className: "modal-copy",
						children: a("common.remoteConflictCopy").replace("remote branch", `remote ${e.branch || "branch"}`)
					}),
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "git-sync-conflict-details",
						children: [
							/* @__PURE__ */ (0, J.jsx)("span", { children: a("label.repository") }),
							/* @__PURE__ */ (0, J.jsx)("code", { children: e.repo || a("common.workspace") }),
							/* @__PURE__ */ (0, J.jsx)("span", { children: a("label.localCommit") }),
							/* @__PURE__ */ (0, J.jsx)("code", { children: e.local_oid || "—" })
						]
					}),
					c && /* @__PURE__ */ (0, J.jsx)("p", {
						className: "git-sync-error",
						role: "alert",
						children: c
					})
				]
			}), /* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
				className: "button",
				disabled: o,
				onClick: r,
				children: a("common.later")
			}), /* @__PURE__ */ (0, J.jsx)("button", {
				className: "button danger",
				disabled: o,
				onClick: () => void u(),
				children: a(o ? "common.overwriting" : "common.overwriteRemote")
			})] })]
		})
	});
}
function M_({ title: e, description: t, action: n }) {
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "page-intro",
		children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("h1", { children: e }), /* @__PURE__ */ (0, J.jsx)("p", { children: t })] }), n]
	});
}
function N_(e, t) {
	let n = [], r = /* @__PURE__ */ new Set(), i = (e, t, i) => {
		let a = (e || t).trim();
		if (!a) return;
		let o = [
			a,
			t,
			e
		].map((e) => e.trim().toLowerCase()).filter(Boolean);
		if (o.some((e) => r.has(e))) return;
		for (let e of o) r.add(e);
		let s = (t || e || a).trim(), c = i.trim();
		n.push({
			value: a,
			label: c ? `${s} · ${c}` : s
		});
	};
	for (let t of e) i(String(t.story || ""), String(t.jira_key || ""), String(t.title || ""));
	return t && /failed|blocked|not_started/i.test(String(t.delivery_status || "")) && i(String(t.story_id || ""), String(t.jira_key || ""), String(t.story_title || "")), n;
}
function P_(e) {
	let t = String(e.businessStatus || "").toLowerCase(), n = String(e.technicalStatus || "").toLowerCase(), r = String(e.deliveryStatus || "not_started").toLowerCase();
	return t === "ready" && n === "approved" && [
		"",
		"not_started",
		"blocked"
	].includes(r);
}
function F_({ agents: e, workflows: t, t: n, onNavigate: r }) {
	let i = {
		dylan: "Engineering Risk Analyst",
		mark: "Delivery Lead",
		irving: "Remediation Engineer",
		milchick: "Engineering Operations Manager"
	}, a = (t, n) => e.find((e) => e.id === t) || (n ? e.find((e) => e.workflow === n) : void 0), o = (e) => e ? !e.app_id || !e.app_secret_configured ? "setup" : e.conversation_enabled ? "ready" : "paused" : "not configured", s = (e, t) => {
		let n = String(e?.id || t.agent).toLowerCase();
		return {
			id: n,
			name: Q(e?.display_name, t.agent),
			title: Q(e?.title, i[n])
		};
	}, c = a("milchick"), l = Jg(Ug, n), u = (e, t) => {
		let i = s(e, t);
		return /* @__PURE__ */ (0, J.jsxs)("button", {
			type: "button",
			className: "agent-team-identity",
			"aria-label": `${n("action.configureAgent")}: ${i.name}`,
			onClick: () => r("settings"),
			children: [/* @__PURE__ */ (0, J.jsx)(qg, {
				agentId: e?.id || i.id,
				displayName: i.name,
				size: "card"
			}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: i.name }), /* @__PURE__ */ (0, J.jsx)("small", { children: i.title })] })]
		});
	}, d = (e) => /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "agent-team-responsibility",
		children: [/* @__PURE__ */ (0, J.jsx)("p", {
			className: "agent-team-mission",
			children: e.mission
		}), /* @__PURE__ */ (0, J.jsxs)("div", {
			className: "agent-team-flow",
			children: [
				/* @__PURE__ */ (0, J.jsx)("span", { children: e.input }),
				/* @__PURE__ */ (0, J.jsx)(Bh, {
					size: 13,
					"aria-hidden": "true"
				}),
				/* @__PURE__ */ (0, J.jsx)("span", { children: e.output })
			]
		})]
	}), f = (e, t) => {
		let n = String(t?.status || "").toLowerCase();
		return /running|progress|active|blocked|failed|awaiting/.test(n) && t?.status || o(e);
	};
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "agent-team-board",
		children: [
			/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "agent-team-entry",
				children: [/* @__PURE__ */ (0, J.jsx)("span", {
					className: "agent-team-entry-icon",
					children: /* @__PURE__ */ (0, J.jsx)("img", {
						src: "assets/feishu-mark.svg",
						alt: "Feishu"
					})
				}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [
					/* @__PURE__ */ (0, J.jsx)("span", {
						className: "overview-kicker",
						children: n("label.entryPoint")
					}),
					/* @__PURE__ */ (0, J.jsx)("strong", { children: n("label.feishuEntry") }),
					/* @__PURE__ */ (0, J.jsx)("small", { children: n("context.activity.description") })
				] })]
			}),
			/* @__PURE__ */ (0, J.jsx)("span", {
				className: "agent-team-connector",
				"aria-hidden": "true"
			}),
			/* @__PURE__ */ (0, J.jsx)("div", {
				className: "agent-team-layer",
				children: /* @__PURE__ */ (0, J.jsxs)("article", {
					className: "agent-team-card agent-team-manager",
					children: [
						/* @__PURE__ */ (0, J.jsxs)("div", {
							className: "agent-team-card-heading",
							children: [u(c, l), /* @__PURE__ */ (0, J.jsx)(a_, { value: o(c) })]
						}),
						d(l),
						/* @__PURE__ */ (0, J.jsx)("footer", {
							className: "agent-team-card-footer",
							children: /* @__PURE__ */ (0, J.jsxs)("button", {
								type: "button",
								className: "text-button",
								onClick: () => r("settings"),
								children: [
									n("action.configureAgent"),
									" ",
									/* @__PURE__ */ (0, J.jsx)(Bh, { size: 13 })
								]
							})
						})
					]
				})
			}),
			/* @__PURE__ */ (0, J.jsx)("span", {
				className: "agent-team-connector",
				"aria-hidden": "true"
			}),
			/* @__PURE__ */ (0, J.jsx)("div", {
				className: "agent-team-capabilities",
				children: /* @__PURE__ */ (0, J.jsx)("div", {
					className: "agent-team-cards",
					children: t.map((e) => {
						let t = a(String(e.agent).toLowerCase(), e.workflow), i = e;
						return /* @__PURE__ */ (0, J.jsxs)("article", {
							className: "agent-team-card",
							children: [
								/* @__PURE__ */ (0, J.jsxs)("div", {
									className: "agent-team-card-heading",
									children: [u(t, i), /* @__PURE__ */ (0, J.jsx)("span", {
										className: "agent-team-statuses",
										children: /* @__PURE__ */ (0, J.jsx)(a_, { value: f(t, e) })
									})]
								}),
								d(i),
								/* @__PURE__ */ (0, J.jsx)("footer", {
									className: "agent-team-card-footer",
									children: /* @__PURE__ */ (0, J.jsxs)("button", {
										type: "button",
										className: "button secondary",
										onClick: () => r(e.tab),
										children: [
											n("action.inspect", { feature: i.feature }),
											" ",
											/* @__PURE__ */ (0, J.jsx)(Bh, { size: 13 })
										]
									})
								})
							]
						}, e.workflow);
					})
				})
			})
		]
	});
}
function I_({ data: e, project: t, onNavigate: n }) {
	let { t: r } = Z(), i = e.interactive?.agents || {}, a = i.agents || [], o = Hg.map((t) => ({
		...Jg(t, r),
		status: t.workflow === "auto_scan" ? e.runs?.[0]?.status || "not started" : t.workflow === "auto_delivery" ? e.delivery?.current?.delivery_status || "not started" : e.patch?.current?.patch_status || "not started"
	})), s = (e) => !e.app_id || !e.app_secret_configured ? "setup" : e.conversation_enabled ? "ready" : "paused", c = a.filter((e) => s(e) === "ready").length, l = o.filter((e) => /running|progress|active/i.test(String(e.status))).length;
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "manager-overview",
		children: [
			/* @__PURE__ */ (0, J.jsx)(M_, {
				title: r("heading.managerOverview"),
				description: `${t || r("common.currentProject")} · ${r("context.overview.description")}`
			}),
			/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "metrics",
				children: [
					/* @__PURE__ */ (0, J.jsx)(U_, {
						label: r("label.agentsReady"),
						value: `${c}/${a.length}`
					}),
					/* @__PURE__ */ (0, J.jsx)(U_, {
						label: r("label.workflowsActive"),
						value: l
					}),
					/* @__PURE__ */ (0, J.jsx)(U_, {
						label: r("label.agentRoles"),
						value: a.length
					}),
					/* @__PURE__ */ (0, J.jsx)(U_, {
						label: r("label.gateway"),
						value: i.enabled ? r("common.enabled") : r("common.paused")
					})
				]
			}),
			/* @__PURE__ */ (0, J.jsx)(k_, {
				title: r("heading.agentTeam"),
				action: /* @__PURE__ */ (0, J.jsxs)("button", {
					className: "text-button",
					onClick: () => n("settings"),
					children: [
						r("action.openSettings"),
						" ",
						/* @__PURE__ */ (0, J.jsx)(Bh, { size: 13 })
					]
				}),
				children: /* @__PURE__ */ (0, J.jsx)(F_, {
					agents: a,
					workflows: o,
					t: r,
					onNavigate: n
				})
			})
		]
	});
}
function L_({ data: e, project: t, onNavigate: n }) {
	let { t: r } = Z(), i = e.activity?.items || [], [a, o] = (0, I.useState)("all"), [s, c] = (0, I.useState)(0), l = i.filter((e) => a === "all" || String(e.agent_id || "") === a), u = Array.from(new Set(i.map((e) => String(e.agent_id || "")).filter(Boolean))), d = i.filter((e) => /completed|success|delegated/i.test(String(e.status || ""))).length, f = i.filter((e) => /failed|blocked|denied/i.test(String(e.status || ""))).length, p = Number(e.activity?.total ?? i.length), m = i.map((e) => Number(e.latency_ms)).filter((e) => Number.isFinite(e) && e >= 0), h = m.length ? t_(Math.round(m.reduce((e, t) => e + t, 0) / m.length)) : "—", g = Math.max(1, Math.ceil(l.length / 10)), _ = l.slice(s * 10, (s + 1) * 10);
	(0, I.useEffect)(() => {
		c(0);
	}, [a]), (0, I.useEffect)(() => {
		c((e) => Math.min(e, g - 1));
	}, [g]);
	let v = (e) => Jg(Wg(String(e.workflow || "")) || R_[String(e.agent_id || "")] || Ug, r);
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "activity-page",
		children: [
			/* @__PURE__ */ (0, J.jsx)(M_, {
				title: r("heading.agentActivity"),
				description: `${t || r("common.currentProject")} · ${r("context.activity.description")}`,
				action: /* @__PURE__ */ (0, J.jsxs)("button", {
					className: "button secondary",
					onClick: () => n("settings"),
					children: [/* @__PURE__ */ (0, J.jsx)(pg, { size: 14 }), r("action.manageCapture")]
				})
			}),
			/* @__PURE__ */ (0, J.jsx)("div", {
				className: "activity-role-guide",
				children: [...Hg, Ug].map((e) => {
					let t = Jg(e, r);
					return /* @__PURE__ */ (0, J.jsxs)("article", { children: [/* @__PURE__ */ (0, J.jsx)(qg, {
						agentId: Kg[t.workflow],
						displayName: t.agent,
						size: "guide"
					}), /* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsxs)("strong", { children: [
						t.agent,
						" · ",
						t.feature
					] }), /* @__PURE__ */ (0, J.jsx)("p", { children: t.mission })] })] }, t.workflow);
				})
			}),
			/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "metrics activity-metrics",
				children: [
					/* @__PURE__ */ (0, J.jsx)(U_, {
						label: r("label.processedQuestions"),
						value: p
					}),
					/* @__PURE__ */ (0, J.jsx)(U_, {
						label: r("label.averageDuration"),
						value: h
					}),
					/* @__PURE__ */ (0, J.jsx)(U_, {
						label: r("label.completed"),
						value: d
					}),
					/* @__PURE__ */ (0, J.jsx)(U_, {
						label: r("label.needsAttention"),
						value: f
					})
				]
			}),
			/* @__PURE__ */ (0, J.jsxs)(k_, {
				title: r("heading.conversationRecords"),
				action: /* @__PURE__ */ (0, J.jsxs)("div", {
					className: "activity-toolbar",
					children: [/* @__PURE__ */ (0, J.jsx)("span", {
						className: "muted",
						children: r("common.showing", { count: l.length })
					}), /* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("span", { children: r("label.role") }), /* @__PURE__ */ (0, J.jsxs)("select", {
						"aria-label": `${r("label.role")} filter`,
						value: a,
						onChange: (e) => o(e.target.value),
						children: [/* @__PURE__ */ (0, J.jsxs)("option", {
							value: "all",
							children: [
								r("common.all"),
								" ",
								r("label.role"),
								"s"
							]
						}), u.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
							value: e,
							children: String(i.find((t) => String(t.agent_id || "") === e)?.display_name || e)
						}, e))]
					})] })]
				}),
				children: [
					!e.activity?.available && /* @__PURE__ */ (0, J.jsxs)("div", {
						className: "activity-note",
						children: [/* @__PURE__ */ (0, J.jsx)(Fh, { size: 15 }), Q(e.activity?.detail, r("common.noAgentHistory"))]
					}),
					_.length ? /* @__PURE__ */ (0, J.jsx)("div", {
						className: "activity-record-list",
						children: _.map((e) => {
							let t = v(e), i = Hg.find((t) => t.workflow === e.workflow), a = String(e.request_text || "").trim(), o = String(e.response_text || "").trim(), s = String(e.prompt_text || "").trim(), c = e.source === "conversation" ? r("label.requestResult") : e.source === "outcome" ? r("label.resultCaptured") : r("label.traceOnly"), l = Array.isArray(e.timeline) ? e.timeline : [];
							return /* @__PURE__ */ (0, J.jsxs)("article", {
								className: "activity-record",
								children: [
									/* @__PURE__ */ (0, J.jsxs)("header", {
										className: "activity-record-header",
										children: [/* @__PURE__ */ (0, J.jsxs)("div", {
											className: "activity-record-identity",
											children: [/* @__PURE__ */ (0, J.jsx)(qg, {
												agentId: e.agent_id,
												displayName: e.display_name || t.agent,
												size: "record"
											}), /* @__PURE__ */ (0, J.jsxs)("div", { children: [
												/* @__PURE__ */ (0, J.jsx)("span", {
													className: "overview-kicker",
													children: t.feature
												}),
												/* @__PURE__ */ (0, J.jsx)("h4", { children: Q(e.display_name, t.agent) }),
												/* @__PURE__ */ (0, J.jsx)("p", { children: Q(e.action, c) })
											] })]
										}), /* @__PURE__ */ (0, J.jsxs)("div", {
											className: "activity-record-status",
											children: [/* @__PURE__ */ (0, J.jsx)(a_, { value: Q(e.status, "unknown") }), /* @__PURE__ */ (0, J.jsx)("time", { children: $g(e.started_at) })]
										})]
									}),
									/* @__PURE__ */ (0, J.jsxs)("div", {
										className: "activity-thread",
										children: [/* @__PURE__ */ (0, J.jsxs)("div", {
											className: "activity-message user",
											children: [/* @__PURE__ */ (0, J.jsx)("span", { children: r("common.you") }), /* @__PURE__ */ (0, J.jsx)(g_, { content: a || r("label.olderTrace") })]
										}), /* @__PURE__ */ (0, J.jsxs)("div", {
											className: "activity-message agent",
											children: [/* @__PURE__ */ (0, J.jsx)("span", { children: Q(e.display_name, t.agent) }), /* @__PURE__ */ (0, J.jsx)(g_, { content: o || r("label.noFinalResponse") })]
										})]
									}),
									/* @__PURE__ */ (0, J.jsxs)("footer", {
										className: "activity-record-footer",
										children: [
											/* @__PURE__ */ (0, J.jsx)("span", { children: c }),
											/* @__PURE__ */ (0, J.jsxs)("span", { children: [
												r("common.trace"),
												" ",
												/* @__PURE__ */ (0, J.jsx)("code", { children: Q(e.trace_id) })
											] }),
											/* @__PURE__ */ (0, J.jsx)("span", { children: e.latency_ms !== void 0 && e.latency_ms !== null ? t_(e.latency_ms) : `${e.event_count || 0} events` }),
											i && /* @__PURE__ */ (0, J.jsxs)("button", {
												className: "text-button",
												onClick: () => n(i.tab),
												children: [
													r("common.open"),
													" ",
													Jg(i, r).feature,
													" ",
													/* @__PURE__ */ (0, J.jsx)(Bh, { size: 13 })
												]
											})
										]
									}),
									/* @__PURE__ */ (0, J.jsxs)("details", {
										className: "activity-debug",
										children: [/* @__PURE__ */ (0, J.jsx)("summary", { children: r("label.debugDetails") }), /* @__PURE__ */ (0, J.jsxs)("div", {
											className: "activity-debug-grid",
											children: [
												/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("span", { children: r("label.input") }), /* @__PURE__ */ (0, J.jsx)(g_, { content: a || r("label.olderTrace") })] }),
												/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("span", { children: r("label.output") }), /* @__PURE__ */ (0, J.jsx)(g_, { content: o || r("label.noFinalResponse") })] }),
												/* @__PURE__ */ (0, J.jsxs)("div", {
													className: "activity-debug-prompt",
													children: [/* @__PURE__ */ (0, J.jsx)("span", { children: r("common.originalPrompt") }), s ? /* @__PURE__ */ (0, J.jsx)("pre", { children: s }) : /* @__PURE__ */ (0, J.jsx)("p", { children: r("label.promptNotCaptured") })]
												})
											]
										})]
									}),
									l.length > 0 && /* @__PURE__ */ (0, J.jsxs)("details", {
										className: "activity-trail",
										children: [/* @__PURE__ */ (0, J.jsx)("summary", { children: r("label.executionTrail") }), /* @__PURE__ */ (0, J.jsx)("div", { children: l.map((e, t) => /* @__PURE__ */ (0, J.jsxs)("p", { children: [
											/* @__PURE__ */ (0, J.jsx)("time", { children: $g(e.at) }),
											/* @__PURE__ */ (0, J.jsx)("strong", { children: Q(e.event) }),
											e.detail && /* @__PURE__ */ (0, J.jsx)("span", { children: Q(e.detail) })
										] }, `${e.event}-${t}`)) })]
									})
								]
							}, String(e.trace_id || `${e.agent_id}-${e.started_at}`));
						})
					}) : /* @__PURE__ */ (0, J.jsxs)("div", {
						className: "activity-empty",
						children: [
							/* @__PURE__ */ (0, J.jsx)(z_, {}),
							/* @__PURE__ */ (0, J.jsx)("strong", { children: r("common.noConversationRecords") }),
							/* @__PURE__ */ (0, J.jsx)("span", { children: e.activity?.available ? r("common.askAgents") : r("common.activityStoreFirstTurn") })
						]
					}),
					l.length > 10 && /* @__PURE__ */ (0, J.jsx)(K_, {
						page: s,
						pageCount: g,
						onChange: c
					})
				]
			}),
			/* @__PURE__ */ (0, J.jsx)("p", {
				className: "activity-retention-note",
				children: r("label.activityRetention")
			})
		]
	});
}
var R_ = {
	dylan: { ...Hg[0] },
	mark: { ...Hg[1] },
	irving: { ...Hg[2] },
	milchick: Ug
};
function z_() {
	return /* @__PURE__ */ (0, J.jsx)("span", {
		className: "activity-empty-icon",
		"aria-hidden": "true",
		children: /* @__PURE__ */ (0, J.jsx)(Fh, { size: 18 })
	});
}
function B_({ data: e, project: t, notify: n, reload: r }) {
	let { t: i } = Z(), a = e.run_stats || {}, o = e.issues || [], s = e.runs || [], [c, l] = (0, I.useState)(null), [u, d] = (0, I.useState)("all"), [f, p] = (0, I.useState)(0), [m, h] = (0, I.useState)(0), [g, _] = (0, I.useState)(!1), [v, y] = (0, I.useState)(""), b = o.filter((e) => [
		"open",
		"in_progress",
		"pr_open",
		"reopened"
	].includes(String(e.status || "").toLowerCase())), x = o.filter((e) => u === "all" || (u === "open" ? [
		"open",
		"in_progress",
		"pr_open",
		"reopened"
	].includes(String(e.status || "").toLowerCase()) : String(e.status || "").toLowerCase() === u)), S = {
		all: o.length,
		open: b.length,
		ignored: o.filter((e) => String(e.status || "").toLowerCase() === "ignored").length,
		resolved: o.filter((e) => String(e.status || "").toLowerCase() === "resolved").length
	}, C = s.slice(f * 10, (f + 1) * 10), w = () => document.getElementById("tracked-findings")?.scrollIntoView({
		behavior: "smooth",
		block: "start"
	}), T = async () => {
		_(!0), y("");
		try {
			await i_("/api/scan/start", t, {
				method: "POST",
				json: {}
			}), h(0), n(`Scan started for ${t}`, "success"), await r().catch(() => void 0);
		} catch (e) {
			let r = e instanceof Error ? e.message : "Unable to start scan", i = r === "Not found" ? `Dashboard is still running an older version. Run \`lumon dashboard stop --project ${t}\`, then open the dashboard again.` : r;
			y(i), n(i, "error");
		} finally {
			_(!1);
		}
	};
	return /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [
		/* @__PURE__ */ (0, J.jsxs)("section", {
			className: "metrics",
			children: [
				/* @__PURE__ */ (0, J.jsx)(U_, {
					label: i("label.openFindings"),
					value: b.length,
					onClick: w
				}),
				/* @__PURE__ */ (0, J.jsx)(U_, {
					label: i("label.successfulScan"),
					value: a.success_7d || 0
				}),
				/* @__PURE__ */ (0, J.jsx)(U_, {
					label: i("label.failed7d"),
					value: a.failed_7d || 0
				}),
				/* @__PURE__ */ (0, J.jsx)(U_, {
					label: i("label.lookbackWindow"),
					value: `${e.scan_window_days || 7}d`
				})
			]
		}),
		/* @__PURE__ */ (0, J.jsxs)(k_, {
			title: i("heading.scanHistory"),
			action: /* @__PURE__ */ (0, J.jsxs)("span", {
				className: "panel-actions",
				children: [/* @__PURE__ */ (0, J.jsxs)("button", {
					type: "button",
					className: "button secondary",
					disabled: g,
					onClick: () => {
						y(""), h(1);
					},
					children: [/* @__PURE__ */ (0, J.jsx)(cg, { size: 14 }), i("action.startScan")]
				}), /* @__PURE__ */ (0, J.jsx)("span", {
					className: "muted",
					children: i("common.runs", { count: s.length })
				})]
			}),
			children: [/* @__PURE__ */ (0, J.jsx)("div", {
				className: "table-scroll",
				children: /* @__PURE__ */ (0, J.jsxs)("table", { children: [/* @__PURE__ */ (0, J.jsx)("thead", { children: /* @__PURE__ */ (0, J.jsxs)("tr", { children: [
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.started") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.status") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.issues") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.duration") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.artifacts") })
				] }) }), /* @__PURE__ */ (0, J.jsx)("tbody", { children: C.map((e) => /* @__PURE__ */ (0, J.jsxs)("tr", { children: [
					/* @__PURE__ */ (0, J.jsx)("td", { children: $g(e.started_at || e.finished_at) }),
					/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)(a_, { value: e.status }) }),
					/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)(G_, { run: e }) }),
					/* @__PURE__ */ (0, J.jsx)("td", { children: Q(e.duration) }),
					/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsxs)("div", {
						className: "artifact-links",
						children: [
							e.html && /* @__PURE__ */ (0, J.jsx)("a", {
								href: `${e.html}?project=${encodeURIComponent(t)}`,
								target: "_blank",
								children: "HTML"
							}),
							e.pdf && /* @__PURE__ */ (0, J.jsx)("a", {
								href: `${e.pdf}?project=${encodeURIComponent(t)}`,
								target: "_blank",
								children: "PDF"
							}),
							!e.html && !e.pdf && "—"
						]
					}) })
				] }, e.id)) })] })
			}), s.length > 10 && /* @__PURE__ */ (0, J.jsx)(K_, {
				page: f,
				pageCount: Math.ceil(s.length / 10),
				onChange: p
			})]
		}),
		/* @__PURE__ */ (0, J.jsxs)(k_, {
			title: i("heading.trackedFindings"),
			action: /* @__PURE__ */ (0, J.jsxs)("span", {
				className: "muted",
				children: [
					x.length,
					" / ",
					o.length,
					" ",
					i("label.issues")
				]
			}),
			children: [/* @__PURE__ */ (0, J.jsx)("div", {
				className: "finding-filters",
				role: "tablist",
				children: [
					"all",
					"open",
					"resolved",
					"ignored"
				].map((e) => /* @__PURE__ */ (0, J.jsxs)("button", {
					className: u === e ? "active" : "",
					onClick: () => d(e),
					children: [
						e === "all" ? i("common.all") : r_(e),
						" ",
						/* @__PURE__ */ (0, J.jsx)("span", { children: S[e] })
					]
				}, e))
			}), /* @__PURE__ */ (0, J.jsx)("div", {
				id: "tracked-findings",
				className: "findings",
				children: x.length ? x.map((e) => /* @__PURE__ */ (0, J.jsx)(q_, {
					issue: e,
					onIgnore: () => l(e)
				}, e.id)) : /* @__PURE__ */ (0, J.jsx)(W_, { label: i("common.noFindings") })
			})]
		}),
		c && /* @__PURE__ */ (0, J.jsx)(Y_, {
			onClose: () => l(null),
			onConfirm: (e) => {
				V_(t, n, r, c.id, e), l(null);
			}
		}),
		m > 0 && /* @__PURE__ */ (0, J.jsx)(H_, {
			project: t,
			step: m === 1 ? 1 : 2,
			busy: g,
			error: v,
			onClose: () => {
				g || h(0);
			},
			onContinue: () => h(2),
			onConfirm: () => void T()
		})
	] });
}
async function V_(e, t, n, r, i) {
	try {
		await i_("/api/issue/ignore", e, {
			method: "POST",
			json: {
				issue_id: r,
				reason: i
			}
		}), t("Finding ignored", "success"), await n();
	} catch (e) {
		t(e instanceof Error ? e.message : "Request failed", "error");
	}
}
function H_({ project: e, step: t, busy: n, error: r, onClose: i, onContinue: a, onConfirm: o }) {
	let { t: s } = Z(), c = t === 1;
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: n ? void 0 : i,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": s(c ? "action.startScan" : "action.confirmScan"),
			onMouseDown: (e) => e.stopPropagation(),
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "modal-body compact",
				children: [
					/* @__PURE__ */ (0, J.jsx)("strong", { children: s(c ? "action.runScan" : "action.confirmScan") }),
					/* @__PURE__ */ (0, J.jsx)("p", {
						className: "modal-copy",
						children: s(c ? "action.scanBody" : "action.scanConfirmBody", { project: e })
					}),
					r && /* @__PURE__ */ (0, J.jsx)("p", {
						className: "status-note",
						children: r
					})
				]
			}), /* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
				className: "button",
				disabled: n,
				onClick: i,
				children: s("common.cancel")
			}), c ? /* @__PURE__ */ (0, J.jsx)("button", {
				className: "button primary",
				disabled: n,
				onClick: a,
				children: s("common.continue")
			}) : /* @__PURE__ */ (0, J.jsxs)("button", {
				className: "button primary",
				disabled: n,
				onClick: o,
				children: [/* @__PURE__ */ (0, J.jsx)(cg, { size: 14 }), n ? s("common.start") + "…" : s("action.startScan")]
			})] })]
		})
	});
}
function U_({ label: e, value: t, onClick: n }) {
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: `metric ${n ? "metric-action" : ""}`,
		onClick: n,
		role: n ? "button" : void 0,
		tabIndex: n ? 0 : void 0,
		onKeyDown: (e) => {
			n && (e.key === "Enter" || e.key === " ") && n();
		},
		children: [/* @__PURE__ */ (0, J.jsx)("span", { children: e }), /* @__PURE__ */ (0, J.jsx)("strong", { children: t })]
	});
}
function W_({ label: e }) {
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "empty",
		children: [/* @__PURE__ */ (0, J.jsx)(mg, { size: 20 }), e]
	});
}
function G_({ run: e }) {
	let { t } = Z(), n = [
		[
			t("label.high"),
			Number(e.high || 0),
			"high"
		],
		[
			t("label.medium"),
			Number(e.medium || 0),
			"medium"
		],
		[
			t("label.low"),
			Number(e.low || 0),
			"low"
		]
	].filter(([, e]) => e > 0);
	return n.length ? /* @__PURE__ */ (0, J.jsx)("span", {
		className: "severity-breakdown",
		children: n.map(([e, t, n]) => /* @__PURE__ */ (0, J.jsxs)("b", {
			className: n,
			children: [
				e,
				": ",
				t
			]
		}, e))
	}) : /* @__PURE__ */ (0, J.jsx)(J.Fragment, { children: "—" });
}
function K_({ page: e, pageCount: t, onChange: n }) {
	let { t: r } = Z();
	return /* @__PURE__ */ (0, J.jsxs)("footer", {
		className: "pagination",
		children: [/* @__PURE__ */ (0, J.jsx)("span", { children: r("common.pageOf", {
			page: e + 1,
			count: t
		}) }), /* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
			className: "button secondary",
			disabled: e === 0,
			onClick: () => n(e - 1),
			children: r("common.previous")
		}), /* @__PURE__ */ (0, J.jsx)("button", {
			className: "button secondary",
			disabled: e === t - 1,
			onClick: () => n(e + 1),
			children: r("common.next")
		})] })]
	});
}
function q_({ issue: e, onIgnore: t }) {
	let { t: n } = Z(), [r, i] = (0, I.useState)(!1), a = e.status || e.issue_status || "open", o = String(a).toLowerCase(), s = !["ignored", "resolved"].includes(o), c = Q(e.jira_key) || Q(e.id);
	return /* @__PURE__ */ (0, J.jsxs)("article", {
		className: "finding",
		children: [/* @__PURE__ */ (0, J.jsxs)("div", {
			className: "finding-main",
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "finding-copy",
				children: [
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "finding-heading",
						children: [/* @__PURE__ */ (0, J.jsx)("h4", { children: Q(e.title, n("label.untitledFinding")) }), /* @__PURE__ */ (0, J.jsx)(a_, { value: a })]
					}),
					/* @__PURE__ */ (0, J.jsxs)("p", {
						className: "finding-meta",
						children: [
							/* @__PURE__ */ (0, J.jsx)("code", {
								className: "finding-id",
								children: c
							}),
							/* @__PURE__ */ (0, J.jsx)("i", { children: "|" }),
							Q(e.repository, n("label.unknownRepository")),
							" ",
							/* @__PURE__ */ (0, J.jsx)("i", { children: "|" }),
							" ",
							$g(e.last_seen_at)
						]
					}),
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "finding-links finding-row-links",
						children: [
							/* @__PURE__ */ (0, J.jsx)("button", {
								className: "finding-link",
								onClick: () => i(!r),
								children: n(r ? "action.hideDetail" : "action.viewDetail")
							}),
							e.jira_key && e.jira_url && /* @__PURE__ */ (0, J.jsxs)("a", {
								className: "finding-link",
								href: e.jira_url,
								target: "_blank",
								rel: "noreferrer",
								children: [e.jira_key, /* @__PURE__ */ (0, J.jsx)(qh, { size: 12 })]
							}),
							e.pr_url && /* @__PURE__ */ (0, J.jsxs)("a", {
								className: "finding-link",
								href: e.pr_url,
								target: "_blank",
								rel: "noreferrer",
								children: [n("action.pullRequest"), /* @__PURE__ */ (0, J.jsx)(qh, { size: 12 })]
							})
						]
					})
				]
			}), /* @__PURE__ */ (0, J.jsx)("div", {
				className: "finding-actions",
				children: s && /* @__PURE__ */ (0, J.jsx)("button", {
					className: "button secondary",
					onClick: t,
					children: n("action.markIgnored")
				})
			})]
		}), r && /* @__PURE__ */ (0, J.jsxs)("div", {
			className: "finding-detail",
			children: [
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: n("label.status"),
					value: r_(a)
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Resolution basis",
					value: e.resolution_basis_label || e.resolution_basis
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: n("label.verification"),
					value: e.verification_label || e.verification_status
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Resolved by",
					value: e.resolved_by
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Resolved at",
					value: $g(e.resolved_at)
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Last verification",
					value: $g(e.last_verified_at)
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Impact",
					value: e.impact
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Trigger",
					value: e.trigger
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Root cause",
					value: e.root_cause
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Code",
					value: e.code_snippet,
					code: !0
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Recommended correction",
					value: e.suggestion
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Validation",
					value: e.validation
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Risk Finding ID",
					value: e.risk_finding_id
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Legacy Issue ID",
					value: e.id
				}),
				/* @__PURE__ */ (0, J.jsx)(J_, {
					label: "Status source",
					value: e.status_source
				})
			]
		})]
	});
}
function J_({ label: e, value: t, code: n = !1 }) {
	return /* @__PURE__ */ (0, J.jsxs)("section", {
		className: "finding-detail-row",
		children: [/* @__PURE__ */ (0, J.jsx)("h5", { children: e }), n ? /* @__PURE__ */ (0, J.jsx)("pre", { children: /* @__PURE__ */ (0, J.jsx)("code", { children: Q(t, "No code snippet was captured for this historical finding.") }) }) : /* @__PURE__ */ (0, J.jsx)("p", { children: Q(t, "Not recorded.") })]
	});
}
function Y_({ onClose: e, onConfirm: t }) {
	let { t: n } = Z(), [r, i] = (0, I.useState)("");
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: e,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": n("action.markIgnored"),
			onMouseDown: (e) => e.stopPropagation(),
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "modal-body compact",
				children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("label.ignoreQuestion") }), /* @__PURE__ */ (0, J.jsx)($, {
					label: n("label.reasonOptional"),
					children: /* @__PURE__ */ (0, J.jsx)("textarea", {
						className: "ignore-reason",
						rows: 2,
						autoFocus: !0,
						value: r,
						onChange: (e) => i(e.target.value),
						placeholder: n("label.ignorePlaceholder")
					})
				})]
			}), /* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
				className: "button",
				onClick: e,
				children: n("common.cancel")
			}), /* @__PURE__ */ (0, J.jsx)("button", {
				className: "button primary",
				onClick: () => t(r),
				children: n("action.markIgnored")
			})] })]
		})
	});
}
function X_({ data: e, project: t, notify: n, reload: r }) {
	let { t: i } = Z(), a = e.delivery || {}, o = a.current || {}, s = a.runs || [], c = o.stages || [], l = a.scheduler_activity || [], u = a.available_stories || [], [d, f] = (0, I.useState)(null), [p, m] = (0, I.useState)(null), [h, g] = (0, I.useState)(""), [_, v] = (0, I.useState)(""), [y, b] = (0, I.useState)(!1), [x, S] = (0, I.useState)(!1), [C, w] = (0, I.useState)(!1), [T, E] = (0, I.useState)(!1), [D, O] = (0, I.useState)(""), [k, ee] = (0, I.useState)(0), [A, j] = (0, I.useState)(""), [M, N] = (0, I.useState)(!1), [P, te] = (0, I.useState)(""), [ne, re] = (0, I.useState)(null), [ie, F] = (0, I.useState)(""), [ae, oe] = (0, I.useState)(Date.now()), se = /in_progress|running|awaiting_deploy/i.test(String(o.delivery_status || "")), ce = o.deployment && typeof o.deployment == "object" ? o.deployment : null, le = N_(u, o), ue = (0, I.useCallback)(async (e = o.run_id || "", n = !1) => {
		n || b(!0);
		try {
			let n = await i_(`/api/delivery/log?run_id=${encodeURIComponent(e)}`, t);
			g(n.content || "No log content recorded."), v("");
		} catch (e) {
			v(e instanceof Error ? e.message : "Unable to load delivery log");
		} finally {
			b(!1);
		}
	}, [o.run_id, t]);
	(0, I.useEffect)(() => {
		if (!se) return;
		let e = window.setInterval(() => oe(Date.now()), 1e3);
		return () => window.clearInterval(e);
	}, [se]);
	let de = !!(d && se && d.run_id === o.run_id && /in_progress|running/i.test(String(d.status || "")));
	(0, I.useEffect)(() => {
		if (!de || !d) return;
		let e = window.setInterval(() => void ue(d.run_id, !0), 2e3);
		return () => window.clearInterval(e);
	}, [
		d,
		de,
		ue
	]);
	let fe = async (e, t = o.run_id || "") => {
		f({
			...e,
			run_id: t
		}), g(""), v(""), await ue(t);
	}, pe = async () => {
		S(!0), g(""), v(""), b(!0);
		try {
			let e = await i_("/api/delivery/scheduler-log", t);
			g(e.content || "No scheduler output recorded.");
		} catch (e) {
			v(e instanceof Error ? e.message : "Unable to load scheduler log");
		} finally {
			b(!1);
		}
	}, me = async () => {
		E(!0), O("");
		try {
			await i_("/api/delivery/retry", t, {
				method: "POST",
				json: {}
			}), w(!1), n("Delivery retry started", "success"), await r().catch(() => void 0);
		} catch (e) {
			let t = e instanceof Error ? e.message : "Unable to retry delivery";
			O(t === "Not found" ? "Dashboard is still running an older version. Run `lumon dashboard stop --project …`, then open the dashboard again." : t);
		} finally {
			E(!1);
		}
	}, he = () => {
		te(""), j(le[0]?.value || ""), ee(1);
	}, ge = async () => {
		let e = A.trim();
		if (!e) {
			n("Select a story to start", "error");
			return;
		}
		N(!0), te("");
		try {
			await i_("/api/delivery/start", t, {
				method: "POST",
				json: { story: e }
			}), ee(0), n(`Delivery started for ${e}`, "success"), await r().catch(() => void 0);
		} catch (e) {
			let t = e instanceof Error ? e.message : "Unable to start delivery";
			te(t), n(t, "error");
		} finally {
			N(!1);
		}
	}, _e = async () => {
		if (window.confirm("Stop this delivery and remove its worktrees?")) {
			N(!0), te("");
			try {
				await i_("/api/delivery/stop", t, {
					method: "POST",
					json: {}
				}), n("Delivery stopped", "success"), await r();
			} catch (e) {
				let t = e instanceof Error ? e.message : "Unable to stop delivery";
				te(t), n(t, "error");
			} finally {
				N(!1);
			}
		}
	}, ve = async (e) => {
		try {
			let n = await i_(`/api/delivery/trace?run_id=${encodeURIComponent(e)}`, t);
			f({
				label: "Trace",
				duration: "Agent evidence",
				detail: "Redacted local execution evidence",
				run_id: e
			}), g(JSON.stringify(n, null, 2)), v("");
		} catch (e) {
			te(e instanceof Error ? e.message : "Unable to load trace");
		}
	}, ye = async () => {
		let e = String(ne?.run_id || "").trim();
		if (e) {
			F(e), te("");
			try {
				await i_("/api/delivery/history/delete", t, {
					method: "POST",
					json: { run_id: e }
				}), re(null), n("Delivery history deleted", "success"), await r().catch(() => void 0);
			} catch (e) {
				let t = e instanceof Error ? e.message : "Unable to delete delivery history";
				te(t), n(t, "error");
			} finally {
				F("");
			}
		}
	}, be = /failed|blocked/i.test(String(o.delivery_status || "")), xe = !se && le.length > 0;
	return /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [
		/* @__PURE__ */ (0, J.jsxs)(k_, {
			title: i("heading.currentProgress"),
			className: "delivery-summary",
			action: /* @__PURE__ */ (0, J.jsxs)("span", {
				className: "panel-actions",
				children: [
					xe && /* @__PURE__ */ (0, J.jsxs)("button", {
						className: "button secondary",
						disabled: M,
						onClick: he,
						children: [/* @__PURE__ */ (0, J.jsx)(cg, { size: 14 }), i("common.start")]
					}),
					se && /* @__PURE__ */ (0, J.jsx)("button", {
						className: "button danger secondary",
						disabled: M,
						onClick: () => void _e(),
						children: i("common.stop")
					}),
					be && /* @__PURE__ */ (0, J.jsxs)("button", {
						className: "button secondary",
						onClick: () => w(!0),
						children: [/* @__PURE__ */ (0, J.jsx)(lg, { size: 14 }), i("common.retry")]
					})
				]
			}),
			children: [
				/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "delivery-facts",
					children: [
						/* @__PURE__ */ (0, J.jsx)(sv, {
							label: i("label.currentStory"),
							value: /* @__PURE__ */ (0, J.jsx)(iv, {
								jiraKey: o.jira_key || o.story_id,
								title: o.story_title
							})
						}),
						/* @__PURE__ */ (0, J.jsx)(sv, {
							label: i("label.status"),
							value: /* @__PURE__ */ (0, J.jsx)(a_, { value: o.delivery_status || "not started" })
						}),
						/* @__PURE__ */ (0, J.jsx)(sv, {
							label: i("label.elapsed"),
							value: e_(o.started_at, o.finished_at || (se ? new Date(ae).toISOString() : void 0))
						}),
						/* @__PURE__ */ (0, J.jsx)(sv, {
							label: i("label.finished"),
							value: se ? i("status.running") : $g(o.finished_at)
						})
					]
				}),
				ce && /* @__PURE__ */ (0, J.jsxs)("div", {
					className: "deployment-tracking",
					children: [
						/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("span", { children: i("label.deployment") }), /* @__PURE__ */ (0, J.jsx)("strong", { children: /* @__PURE__ */ (0, J.jsx)(a_, { value: ce.status || "queued" }) })] }),
						/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("span", { children: i("label.provider") }), /* @__PURE__ */ (0, J.jsx)("strong", { children: Q(String(ce.provider || "").replaceAll("_", " ")) })] }),
						/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("span", { children: i("label.lastChecked") }), /* @__PURE__ */ (0, J.jsx)("strong", { children: $g(ce.last_checked_at) })] }),
						ce.url && /* @__PURE__ */ (0, J.jsxs)("a", {
							href: ce.url,
							target: "_blank",
							rel: "noreferrer",
							children: [
								i("action.openDeployment"),
								" ",
								/* @__PURE__ */ (0, J.jsx)(qh, { size: 12 })
							]
						}),
						/* @__PURE__ */ (0, J.jsx)("p", { children: Q(ce.detail, i("settings.deploymentTrackingDescription")) })
					]
				}),
				P && /* @__PURE__ */ (0, J.jsx)("div", {
					className: "status-note",
					children: P
				}),
				/* @__PURE__ */ (0, J.jsx)(av, {
					stages: c,
					deliveryStatus: String(o.delivery_status || ""),
					currentStep: String(o.current_step || ""),
					startedAt: o.started_at,
					finishedAt: o.finished_at,
					remediation: o.remediation,
					now: ae,
					onStageClick: fe
				})
			]
		}),
		/* @__PURE__ */ (0, J.jsx)(k_, {
			title: i("heading.deliveryHistory"),
			className: "history-panel",
			action: /* @__PURE__ */ (0, J.jsx)("span", {
				className: "muted",
				children: i("common.runs", { count: s.length })
			}),
			children: /* @__PURE__ */ (0, J.jsx)("div", {
				className: "table-scroll",
				children: /* @__PURE__ */ (0, J.jsxs)("table", { children: [/* @__PURE__ */ (0, J.jsx)("thead", { children: /* @__PURE__ */ (0, J.jsxs)("tr", { children: [
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.story") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.finishedAt") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.status") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.pullRequests") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.checks") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.duration") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.trace") }),
					/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.operation") })
				] }) }), /* @__PURE__ */ (0, J.jsx)("tbody", { children: s.length ? s.map((e) => {
					let t = e.verification || [], n = t.filter((e) => e.status === "failed"), r = n.length || /failed|blocked/i.test(String(e.status));
					return /* @__PURE__ */ (0, J.jsxs)("tr", { children: [
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "history-story",
							children: [/* @__PURE__ */ (0, J.jsxs)("span", {
								className: "history-story-line",
								children: [/* @__PURE__ */ (0, J.jsx)("code", { children: Q(e.jira_key || e.story || e.run_id) }), e.story_title && /* @__PURE__ */ (0, J.jsx)("span", {
									className: "history-story-title",
									children: e.story_title
								})]
							}), /* @__PURE__ */ (0, J.jsx)("small", { children: Q(e.branch, "") })]
						}) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: $g(e.finished_at || e.started_at) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: r ? /* @__PURE__ */ (0, J.jsx)("button", {
							className: "status-badge-button",
							title: i("action.openLog"),
							onClick: () => void fe({
								label: "Delivery failure",
								duration: e_(e.started_at, e.finished_at),
								detail: n.map((e) => e.summary || e.label).filter(Boolean).join(" · ") || "Open the delivery log for details."
							}, e.run_id),
							children: /* @__PURE__ */ (0, J.jsx)(a_, { value: e.status })
						}) : /* @__PURE__ */ (0, J.jsx)(a_, { value: e.status }) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)(cv, { items: e.pull_requests || [] }) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)(lv, {
							checks: t,
							onClick: () => m(t)
						}) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: e_(e.started_at, e.finished_at) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: e.agent_trace && /* @__PURE__ */ (0, J.jsx)("button", {
							className: "text-button",
							onClick: () => void ve(e.run_id),
							children: i("common.viewTrace")
						}) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)(O_, {
							label: "Delete delivery record",
							danger: !0,
							disabled: ie === e.run_id,
							onClick: () => re(e),
							children: /* @__PURE__ */ (0, J.jsx)(_g, { size: 15 })
						}) })
					] }, e.run_id);
				}) : /* @__PURE__ */ (0, J.jsx)("tr", { children: /* @__PURE__ */ (0, J.jsx)("td", {
					colSpan: 8,
					children: /* @__PURE__ */ (0, J.jsx)(W_, { label: i("common.noDeliveryHistory") })
				}) }) })] })
			})
		}),
		/* @__PURE__ */ (0, J.jsx)(k_, {
			title: i("heading.schedulerActivity"),
			action: /* @__PURE__ */ (0, J.jsxs)("span", {
				className: "panel-actions",
				children: [/* @__PURE__ */ (0, J.jsx)("span", {
					className: "muted",
					children: i("common.recentEvents", { count: l.length })
				}), a.scheduler_log_available && /* @__PURE__ */ (0, J.jsxs)("button", {
					className: "button secondary",
					onClick: () => void pe(),
					children: [/* @__PURE__ */ (0, J.jsx)(gg, { size: 14 }), i("action.viewRawLog")]
				})]
			}),
			children: /* @__PURE__ */ (0, J.jsx)("div", {
				className: "scheduler-activity",
				children: l.length ? l.map((e, t) => /* @__PURE__ */ (0, J.jsxs)("article", {
					className: "scheduler-event",
					children: [
						/* @__PURE__ */ (0, J.jsx)(a_, { value: e.outcome }),
						/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: Q(e.story_id || e.jira_key, i("common.workspace")) }), /* @__PURE__ */ (0, J.jsx)("p", { children: Q(e.message) })] }),
						/* @__PURE__ */ (0, J.jsx)("time", { children: $g(e.at) })
					]
				}, `${e.at}-${t}`)) : /* @__PURE__ */ (0, J.jsx)(W_, { label: i("common.noDeliveryActivity") })
			})
		}),
		d && /* @__PURE__ */ (0, J.jsx)(ov, {
			stage: d,
			content: h,
			error: _,
			loading: y,
			live: de,
			onClose: () => f(null)
		}),
		x && /* @__PURE__ */ (0, J.jsx)(ov, {
			stage: {
				label: "Scheduler log",
				duration: "Recent raw output",
				detail: "Launchd output is capped at 256 KiB; structured activity retains the latest 200 events."
			},
			content: h,
			error: _,
			loading: y,
			onClose: () => S(!1)
		}),
		p && /* @__PURE__ */ (0, J.jsx)(uv, {
			checks: p,
			onClose: () => m(null)
		}),
		C && /* @__PURE__ */ (0, J.jsx)(tv, {
			story: Q(o.jira_key || o.story_id),
			busy: T,
			error: D,
			onClose: () => w(!1),
			onConfirm: () => void me()
		}),
		k > 0 && /* @__PURE__ */ (0, J.jsx)(ev, {
			stories: le,
			value: A,
			onChange: j,
			step: k === 1 ? 1 : 2,
			busy: M,
			error: P,
			onClose: () => {
				M || ee(0);
			},
			onContinue: () => ee(2),
			onConfirm: () => void ge()
		}),
		ne && /* @__PURE__ */ (0, J.jsx)(nv, {
			run: ne,
			busy: !!ie,
			onClose: () => re(null),
			onConfirm: () => void ye()
		})
	] });
}
function Z_({ data: e, project: t, notify: n, reload: r }) {
	let { t: i } = Z(), a = e.patch || {}, o = a.current || {}, s = a.runs || [], c = a.scheduler_activity || [], l = !!o.active || /in_progress|running/i.test(String(o.patch_status || "")), [u, d] = (0, I.useState)(""), [f, p] = (0, I.useState)(""), [m, h] = (0, I.useState)(!1), [g, _] = (0, I.useState)(!1), [v, y] = (0, I.useState)(null), [b, x] = (0, I.useState)(""), [S, C] = (0, I.useState)(""), [w, T] = (0, I.useState)(!1), [E, D] = (0, I.useState)(!1), [O, k] = (0, I.useState)(""), [ee, A] = (0, I.useState)([]), [j, M] = (0, I.useState)(""), N = async (e = String(o.run_id || "")) => {
		h(!0), d(""), p("");
		try {
			let n = await i_(`/api/patch/log?run_id=${encodeURIComponent(e)}`, t);
			d(n.content || "No log content recorded.");
		} catch (e) {
			p(e instanceof Error ? e.message : "Unable to load Auto Patch log");
		}
	}, P = async () => {
		T(!0), D(!0), k(""), A([]), M("");
		try {
			let e = await i_("/api/patch/candidates", t), n = Array.isArray(e.candidates) ? e.candidates : [];
			A(n), M(String(n.find((e) => e.available)?.jira_key || ""));
		} catch (e) {
			k(e instanceof Error ? e.message : "Unable to load Auto Patch candidates");
		} finally {
			D(!1);
		}
	}, te = async (e = "") => {
		_(!0);
		try {
			await i_("/api/patch/start", t, {
				method: "POST",
				json: { jira_key: e }
			}), T(!1), n("Auto Patch started", "success"), await r();
		} catch (e) {
			n(e instanceof Error ? e.message : "Unable to start Auto Patch", "error");
		} finally {
			_(!1);
		}
	}, ne = async () => {
		_(!0);
		try {
			await i_("/api/patch/stop", t, {
				method: "POST",
				json: {}
			}), n("Auto Patch stopped", "success"), await r();
		} catch (e) {
			n(e instanceof Error ? e.message : "Unable to stop Auto Patch", "error");
		} finally {
			_(!1);
		}
	}, re = async () => {
		let e = String(v?.run_id || "").trim();
		if (e) {
			x(e), C("");
			try {
				await i_("/api/patch/history/delete", t, {
					method: "POST",
					json: { run_id: e }
				}), y(null), n("Patch history deleted", "success"), await r().catch(() => void 0);
			} catch (e) {
				let t = e instanceof Error ? e.message : "Unable to delete Auto Patch history";
				C(t), n(t, "error");
			} finally {
				x("");
			}
		}
	};
	return /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [
		/* @__PURE__ */ (0, J.jsxs)(k_, {
			title: i("heading.currentProgress"),
			action: /* @__PURE__ */ (0, J.jsx)("span", {
				className: "panel-actions",
				children: l ? /* @__PURE__ */ (0, J.jsx)("button", {
					className: "button danger secondary",
					disabled: g,
					onClick: () => void ne(),
					children: i("common.stop")
				}) : /* @__PURE__ */ (0, J.jsxs)("button", {
					className: "button secondary",
					disabled: g,
					onClick: () => void P(),
					children: [/* @__PURE__ */ (0, J.jsx)(cg, { size: 14 }), i("action.runCycle")]
				})
			}),
			children: [
				/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "delivery-facts",
					children: [
						/* @__PURE__ */ (0, J.jsx)(sv, {
							label: i("label.jiraCard"),
							value: /* @__PURE__ */ (0, J.jsx)(iv, {
								jiraKey: o.jira_key,
								title: o.jira_summary
							})
						}),
						/* @__PURE__ */ (0, J.jsx)(sv, {
							label: i("label.status"),
							value: /* @__PURE__ */ (0, J.jsx)(a_, { value: o.patch_status || "not started" })
						}),
						/* @__PURE__ */ (0, J.jsx)(sv, {
							label: i("label.branch"),
							value: /* @__PURE__ */ (0, J.jsx)("code", { children: Q(o.branch) })
						}),
						/* @__PURE__ */ (0, J.jsx)(sv, {
							label: i("label.repositories"),
							value: Array.isArray(o.repositories) && o.repositories.map((e) => e.name).filter(Boolean).join(", ") || "—"
						})
					]
				}),
				o.question && /* @__PURE__ */ (0, J.jsxs)("div", {
					className: "status-note",
					children: [/* @__PURE__ */ (0, J.jsx)(Wh, { size: 15 }), o.question]
				}),
				/* @__PURE__ */ (0, J.jsx)($_, {
					phases: Array.isArray(o.stages) ? o.stages : [],
					overallStatus: String(o.patch_status || "")
				})
			]
		}),
		/* @__PURE__ */ (0, J.jsxs)(k_, {
			title: i("heading.patchHistory"),
			action: /* @__PURE__ */ (0, J.jsx)("span", {
				className: "muted",
				children: i("common.runs", { count: s.length })
			}),
			children: [S && /* @__PURE__ */ (0, J.jsx)("div", {
				className: "status-note",
				children: S
			}), /* @__PURE__ */ (0, J.jsx)("div", {
				className: "table-scroll patch-history-scroll",
				children: /* @__PURE__ */ (0, J.jsxs)("table", {
					className: "patch-history-table",
					children: [/* @__PURE__ */ (0, J.jsx)("thead", { children: /* @__PURE__ */ (0, J.jsxs)("tr", { children: [
						/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.jira") }),
						/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.summary") }),
						/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.status") }),
						/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.repositories") }),
						/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.finishedAt") }),
						/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.log") }),
						/* @__PURE__ */ (0, J.jsx)("th", { children: i("label.operation") })
					] }) }), /* @__PURE__ */ (0, J.jsx)("tbody", { children: s.length ? s.map((e) => /* @__PURE__ */ (0, J.jsxs)("tr", { children: [
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "patch-history-jira",
							children: [/* @__PURE__ */ (0, J.jsx)("span", {
								className: "patch-history-key",
								children: Q(e.jira_key)
							}), e.jira_summary && /* @__PURE__ */ (0, J.jsx)("span", {
								className: "patch-history-jira-title",
								title: Q(e.jira_summary),
								children: Q(e.jira_summary)
							})]
						}) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)("span", {
							className: "patch-history-summary",
							title: Q(e.summary),
							children: Q(e.summary)
						}) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)(a_, { value: e.status }) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: (e.repositories || []).map((e) => e.name).filter(Boolean).join(", ") || "—" }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)("span", {
							className: "patch-history-finished",
							children: $g(e.finished_at)
						}) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)("button", {
							className: "text-button",
							onClick: () => void N(e.run_id),
							children: i("common.viewLog")
						}) }),
						/* @__PURE__ */ (0, J.jsx)("td", { children: /* @__PURE__ */ (0, J.jsx)(O_, {
							label: "Delete Auto Patch record",
							danger: !0,
							disabled: b === e.run_id,
							onClick: () => y(e),
							children: /* @__PURE__ */ (0, J.jsx)(_g, { size: 15 })
						}) })
					] }, e.run_id)) : /* @__PURE__ */ (0, J.jsx)("tr", { children: /* @__PURE__ */ (0, J.jsx)("td", {
						colSpan: 7,
						children: /* @__PURE__ */ (0, J.jsx)(W_, { label: i("common.noPatchHistory") })
					}) }) })]
				})
			})]
		}),
		/* @__PURE__ */ (0, J.jsx)(k_, {
			title: i("heading.schedulerActivity"),
			children: /* @__PURE__ */ (0, J.jsx)("div", {
				className: "scheduler-activity",
				children: c.length ? c.map((e, t) => /* @__PURE__ */ (0, J.jsxs)("article", {
					className: "scheduler-event",
					children: [
						/* @__PURE__ */ (0, J.jsx)(a_, { value: e.outcome }),
						/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: Q(e.jira_key || e.card, i("common.workspace")) }), /* @__PURE__ */ (0, J.jsx)("p", { children: Q(e.message) })] }),
						/* @__PURE__ */ (0, J.jsx)("time", { children: $g(e.at) })
					]
				}, `${e.at}-${t}`)) : /* @__PURE__ */ (0, J.jsx)(W_, { label: i("common.noPatchActivity") })
			})
		}),
		w && /* @__PURE__ */ (0, J.jsx)(Q_, {
			candidates: ee,
			selected: j,
			loading: E,
			error: O,
			busy: g,
			onChange: M,
			onClose: () => {
				g || T(!1);
			},
			onConfirm: () => void te(j)
		}),
		m && /* @__PURE__ */ (0, J.jsx)(ov, {
			stage: {
				label: "Auto Patch log",
				detail: "Recent Auto Patch agent output"
			},
			content: u,
			error: f,
			loading: !u && !f,
			onClose: () => h(!1)
		}),
		v && /* @__PURE__ */ (0, J.jsx)(nv, {
			kind: "patch",
			run: v,
			busy: !!b,
			onClose: () => y(null),
			onConfirm: () => void re()
		})
	] });
}
function Q_({ candidates: e, selected: t, loading: n, error: r, busy: i, onChange: a, onClose: o, onConfirm: s }) {
	let { t: c } = Z(), l = e.filter((e) => e.available), u = !n && !r && !e.length, d = !n && !!r, f = n ? `${c("label.autoPatch")} · ${c("common.loading")}` : d ? `${c("label.autoPatch")} · ${c("status.notSet")}` : u ? `${c("label.autoPatch")} · ${c("common.noData")}` : `${c("label.autoPatch")} · ${c("common.selectStory")}`;
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: i ? void 0 : o,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal patch-candidate-modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": f,
			onMouseDown: (e) => e.stopPropagation(),
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "modal-body compact",
				children: [
					/* @__PURE__ */ (0, J.jsx)("strong", { children: f }),
					/* @__PURE__ */ (0, J.jsx)("p", {
						className: "modal-copy",
						children: c("common.onlyTaskBugCards")
					}),
					n && /* @__PURE__ */ (0, J.jsx)("div", {
						className: "patch-candidate-empty",
						children: c("common.loading")
					}),
					d && /* @__PURE__ */ (0, J.jsxs)("div", {
						className: "patch-candidate-error",
						children: [/* @__PURE__ */ (0, J.jsx)(Vh, { size: 17 }), /* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: c("common.unableLoadState") }), /* @__PURE__ */ (0, J.jsx)("p", { children: r })] })]
					}),
					u && /* @__PURE__ */ (0, J.jsx)("div", {
						className: "patch-candidate-empty",
						children: c("common.noPendingPatchCards")
					}),
					!n && !r && e.length > 0 && /* @__PURE__ */ (0, J.jsx)("div", {
						className: "patch-candidate-list",
						children: e.map((e) => {
							let n = String(e.jira_key || ""), r = !e.available;
							return /* @__PURE__ */ (0, J.jsxs)("label", {
								className: `patch-candidate-option${t === n ? " selected" : ""}${r ? " disabled" : ""}`,
								children: [/* @__PURE__ */ (0, J.jsx)("input", {
									type: "radio",
									name: "patch-candidate",
									value: n,
									checked: t === n,
									disabled: r || i,
									onChange: () => a(n)
								}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [
									/* @__PURE__ */ (0, J.jsxs)("strong", { children: [
										n,
										" · ",
										Q(e.summary)
									] }),
									/* @__PURE__ */ (0, J.jsxs)("small", { children: [
										Q(e.issue_type, "Task"),
										" · ",
										Q(e.status, "Unknown status"),
										e.priority ? ` · Priority ${e.priority}` : ""
									] }),
									e.reason && /* @__PURE__ */ (0, J.jsx)("em", { children: e.reason })
								] })]
							}, n);
						})
					})
				]
			}), /* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
				className: "button",
				disabled: i,
				onClick: o,
				children: c("common.close")
			}), !u && !d && /* @__PURE__ */ (0, J.jsxs)("button", {
				className: "button primary",
				disabled: i || !t || l.length === 0,
				onClick: s,
				children: [/* @__PURE__ */ (0, J.jsx)(cg, { size: 14 }), i ? `${c("common.start")}…` : `${c("common.start")} ${c("label.autoPatch")}`]
			})] })]
		})
	});
}
function $_({ phases: e, overallStatus: t }) {
	let { t: n } = Z(), r = e.filter((e) => !["screen", "context"].includes(String(e.id || "").toLowerCase())), i = String(t).toLowerCase() === "skipped", a = r.filter((e) => e.status === "completed").length, o = i ? r.length > 1 ? Math.round(Math.max(a - 1, 0) / (r.length - 1) * 100) : 0 : r.length ? Math.round(a / r.length * 100) : 0;
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "delivery-flow patch-flow",
		children: [/* @__PURE__ */ (0, J.jsxs)("div", {
			className: "flow-heading",
			children: [/* @__PURE__ */ (0, J.jsx)("div", { children: /* @__PURE__ */ (0, J.jsxs)("span", {
				className: "flow-title",
				children: [n("label.autoPatch"), " Flow"]
			}) }), /* @__PURE__ */ (0, J.jsx)("p", { children: n("common.patchFlow") })]
		}), /* @__PURE__ */ (0, J.jsxs)("div", {
			className: "flow-track-wrap",
			children: [/* @__PURE__ */ (0, J.jsx)("span", {
				className: "flow-track",
				children: /* @__PURE__ */ (0, J.jsx)("i", { style: { width: `${o}%` } })
			}), /* @__PURE__ */ (0, J.jsx)("ol", {
				className: "flow-steps",
				style: { "--flow-count": Math.max(r.length, 1) },
				children: r.map((e, t) => {
					let r = String(e.status || "pending").toLowerCase(), a = i && r !== "completed" ? "skipped" : r === "completed" ? "completed" : /in_progress|running/.test(r) ? "running" : /failed|blocked/.test(r) ? "failed" : "pending", o = Q(e.detail || e.status, n("label.pending")), s = e.started_at ? e_(e.started_at, e.finished_at || (/* @__PURE__ */ new Date()).toISOString()) : "—";
					return /* @__PURE__ */ (0, J.jsx)("li", {
						className: `flow-step ${a}`,
						children: /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "flow-stage-button",
							children: [/* @__PURE__ */ (0, J.jsx)("span", {
								className: "flow-marker",
								children: a === "completed" ? "✓" : a === "skipped" ? "–" : t + 1
							}), /* @__PURE__ */ (0, J.jsxs)("span", {
								className: "flow-copy",
								children: [
									/* @__PURE__ */ (0, J.jsx)("strong", { children: Q(e.label) }),
									/* @__PURE__ */ (0, J.jsx)("span", {
										className: "flow-detail",
										title: o,
										children: o
									}),
									/* @__PURE__ */ (0, J.jsx)("small", {
										className: "flow-duration",
										children: s
									})
								]
							})]
						})
					}, e.id || t);
				})
			})]
		})]
	});
}
function ev({ stories: e, value: t, onChange: n, step: r, busy: i, error: a, onClose: o, onContinue: s, onConfirm: c }) {
	let { t: l } = Z(), u = r === 1, d = e.find((e) => e.value === t)?.label || t;
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: i ? void 0 : o,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": l("label.autoDelivery"),
			onMouseDown: (e) => e.stopPropagation(),
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "modal-body compact",
				children: [
					/* @__PURE__ */ (0, J.jsx)("strong", { children: u ? l("action.startDelivery") : `${l("action.startDelivery")} · ${l("common.confirm")}` }),
					/* @__PURE__ */ (0, J.jsx)("p", {
						className: "modal-copy",
						children: u ? "Choose a ready story to launch." : `Are you sure you want to start delivery for ${d} now?`
					}),
					u && /* @__PURE__ */ (0, J.jsxs)("label", {
						className: "field",
						children: [/* @__PURE__ */ (0, J.jsx)("span", { children: l("label.story") }), /* @__PURE__ */ (0, J.jsx)("select", {
							value: t,
							onChange: (e) => n(e.target.value),
							disabled: i || e.length === 0,
							children: e.length ? e.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
								value: e.value,
								title: e.label,
								children: e.label
							}, e.value)) : /* @__PURE__ */ (0, J.jsx)("option", {
								value: "",
								children: l("common.noData")
							})
						})]
					}),
					a && /* @__PURE__ */ (0, J.jsx)("p", {
						className: "status-note",
						children: a
					})
				]
			}), /* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
				className: "button",
				disabled: i,
				onClick: o,
				children: l("common.cancel")
			}), u ? /* @__PURE__ */ (0, J.jsx)("button", {
				className: "button primary",
				disabled: i || !t,
				onClick: s,
				children: l("common.continue")
			}) : /* @__PURE__ */ (0, J.jsxs)("button", {
				className: "button primary",
				disabled: i || !t,
				onClick: c,
				children: [/* @__PURE__ */ (0, J.jsx)(cg, { size: 14 }), i ? `${l("common.start")}…` : l("action.startDelivery")]
			})] })]
		})
	});
}
function tv({ story: e, busy: t, error: n, onClose: r, onConfirm: i }) {
	let { t: a } = Z();
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: t ? void 0 : r,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": `${a("common.retry")} ${a("label.autoDelivery")}`,
			onMouseDown: (e) => e.stopPropagation(),
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "modal-body compact",
				children: [
					/* @__PURE__ */ (0, J.jsxs)("strong", { children: [
						a("common.retry"),
						" ",
						e,
						"?"
					] }),
					/* @__PURE__ */ (0, J.jsx)("p", { children: a("common.retryDeliveryCopy") }),
					n && /* @__PURE__ */ (0, J.jsx)("p", {
						className: "status-note",
						children: n
					})
				]
			}), /* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
				className: "button",
				disabled: t,
				onClick: r,
				children: a("common.cancel")
			}), /* @__PURE__ */ (0, J.jsxs)("button", {
				className: "button primary",
				disabled: t,
				onClick: i,
				children: [/* @__PURE__ */ (0, J.jsx)(lg, { size: 14 }), t ? `${a("common.start")}…` : a("common.retry")]
			})] })]
		})
	});
}
function nv({ kind: e = "delivery", run: t, busy: n, onClose: r, onConfirm: i }) {
	let { t: a } = Z(), o = e === "patch", s = Q(t.jira_key || t.story || t.run_id), c = a(o ? "label.autoPatch" : "label.autoDelivery");
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: n ? void 0 : r,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal delete-history-modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": `${c} history`,
			onMouseDown: (e) => e.stopPropagation(),
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "modal-body compact",
				children: [/* @__PURE__ */ (0, J.jsxs)("strong", { children: [
					"Delete ",
					c,
					" history?"
				] }), /* @__PURE__ */ (0, J.jsxs)("p", {
					className: "modal-copy",
					children: [
						"This removes the ",
						s,
						" record, log, and trace files. This action cannot be undone."
					]
				})]
			}), /* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
				className: "button",
				disabled: n,
				onClick: r,
				children: a("common.cancel")
			}), /* @__PURE__ */ (0, J.jsxs)("button", {
				className: "button danger delete-confirm",
				disabled: n,
				onClick: i,
				children: [/* @__PURE__ */ (0, J.jsx)(_g, { size: 14 }), n ? "Deleting…" : "Delete record"]
			})] })]
		})
	});
}
function rv({ project: e, notify: t, onDirtyChange: n }) {
	let { t: r } = Z(), i = new URLSearchParams(window.location.search).get("story") || "", [a, o] = (0, I.useState)([]), [s, c] = (0, I.useState)(i), [l, u] = (0, I.useState)(""), [d, f] = (0, I.useState)(""), [p, m] = (0, I.useState)(""), [h, g] = (0, I.useState)(""), [_, v] = (0, I.useState)(""), [y, b] = (0, I.useState)(""), [x, S] = (0, I.useState)(""), [C, w] = (0, I.useState)({
		story: "",
		plan: ""
	}), [T, E] = (0, I.useState)("story"), [D, O] = (0, I.useState)(!0), [k, ee] = (0, I.useState)(!1), [A, j] = (0, I.useState)(!1), [M, N] = (0, I.useState)(""), [P, te] = (0, I.useState)(!1), [ne, re] = (0, I.useState)(!1), [ie, F] = (0, I.useState)(0), [ae, oe] = (0, I.useState)(""), [se, ce] = (0, I.useState)(!1), [le, ue] = (0, I.useState)(""), de = y !== C.story || x !== C.plan, fe = N_(a.filter(P_)), pe = fe.length > 0;
	(0, I.useEffect)(() => {
		n(de);
	}, [de, n]), (0, I.useEffect)(() => {
		let e = (e) => {
			de && (e.preventDefault(), e.returnValue = "");
		};
		return window.addEventListener("beforeunload", e), () => window.removeEventListener("beforeunload", e);
	}, [de]);
	let me = (0, I.useCallback)(async () => {
		O(!0);
		try {
			let t = await i_("/api/stories", e), n = Array.isArray(t.stories) ? t.stories : [];
			o(n), c((e) => e && n.some((t) => t.story === e) ? e : String(n[0]?.story || ""));
		} catch (e) {
			t(e instanceof Error ? e.message : "Unable to load stories", "error");
		} finally {
			O(!1);
		}
	}, [e, t]), he = (0, I.useCallback)(async (n) => {
		if (n) {
			ee(!0), E("story");
			try {
				let t = await i_(`/api/stories/content?story=${encodeURIComponent(n)}`, e);
				u(String(t.title || "")), f(String(t.jira_key || "")), m(String(t.jira_url || "")), g(String(t.businessStatus || "")), v(String(t.technicalStatus || ""));
				let r = String(t.story_markdown || ""), i = String(t.plan_markdown || "");
				b(r), S(i), w({
					story: r,
					plan: i
				});
				let a = new URL(window.location.href);
				a.searchParams.set("story", n), window.history.replaceState({}, "", `${a.pathname}${a.search}`);
			} catch (e) {
				t(e instanceof Error ? e.message : "Unable to load story content", "error");
			} finally {
				ee(!1);
			}
		}
	}, [e, t]);
	(0, I.useEffect)(() => {
		me();
	}, [me]), (0, I.useEffect)(() => {
		s && he(s);
	}, [s, he]);
	let ge = (e) => {
		e !== s && (de && !window.confirm(r("common.unsavedObservatory")) || c(e));
	}, _e = () => {
		ue("");
		let e = fe.find((e) => e.value === s)?.value || fe[0]?.value || "";
		oe(e), F(1);
	}, ve = async () => {
		let n = ae.trim();
		if (!n) {
			t("Select a story to start", "error");
			return;
		}
		if (!(de && !window.confirm(r("common.unsavedObservatory")))) {
			ce(!0), ue("");
			try {
				await i_("/api/delivery/start", e, {
					method: "POST",
					json: { story: n }
				}), F(0), t(`Delivery started for ${n}`, "success"), await me();
			} catch (e) {
				let n = e instanceof Error ? e.message : "Unable to start delivery";
				ue(n), t(n, "error");
			} finally {
				ce(!1);
			}
		}
	}, ye = async () => {
		if (!(!s || !de)) {
			j(!0);
			try {
				let n = await i_("/api/stories/content", e, {
					method: "POST",
					json: {
						story: s,
						story_markdown: y,
						plan_markdown: x
					}
				});
				w({
					story: y,
					plan: x
				}), t(String(n.subject || "Story docs saved"), "success"), await me();
			} catch (e) {
				t(e instanceof Error ? e.message : "Unable to save story docs", "error");
			} finally {
				j(!1);
			}
		}
	}, be = Q(d || s), xe = Q(l, s), L = a.filter((e) => {
		if (ne && String(e.businessStatus || "").toLowerCase() !== "ready") return !1;
		let t = M.trim().toLowerCase();
		return !t || `${e.jira_key || ""} ${e.title || ""} ${e.story || ""} ${e.assignee || ""}`.toLowerCase().includes(t);
	}).slice().sort((e, t) => {
		let n = String(e.updatedAt || e.createdAt || ""), r = String(t.updatedAt || t.createdAt || "");
		return n === r ? String(t.story || "").localeCompare(String(e.story || "")) : r.localeCompare(n);
	});
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "observatory-layout",
		children: [
			/* @__PURE__ */ (0, J.jsxs)("aside", {
				className: "observatory-list panel",
				children: [
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "panel-header observatory-list-header",
						children: [/* @__PURE__ */ (0, J.jsx)("h3", { children: r("heading.stories") }), /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "observatory-list-tools",
							children: [/* @__PURE__ */ (0, J.jsx)("button", {
								type: "button",
								className: `icon-button${P ? " active" : ""}`,
								title: r("action.searchStories"),
								"aria-label": r("action.searchStories"),
								"aria-pressed": P,
								onClick: () => te((e) => !e),
								children: /* @__PURE__ */ (0, J.jsx)(fg, { size: 15 })
							}), /* @__PURE__ */ (0, J.jsx)("button", {
								type: "button",
								className: `icon-button${ne ? " active" : ""}`,
								title: r(ne ? "action.showingReadyStories" : "action.filterReadyStories"),
								"aria-label": r("action.filterStories"),
								"aria-pressed": ne,
								onClick: () => re((e) => !e),
								children: /* @__PURE__ */ (0, J.jsx)(rg, { size: 15 })
							})]
						})]
					}),
					P && /* @__PURE__ */ (0, J.jsx)("div", {
						className: "observatory-list-search",
						children: /* @__PURE__ */ (0, J.jsx)("input", {
							value: M,
							onChange: (e) => N(e.target.value),
							placeholder: r("action.searchStories"),
							"aria-label": r("action.searchStories"),
							autoFocus: !0
						})
					}),
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "observatory-list-body",
						children: [
							D ? /* @__PURE__ */ (0, J.jsxs)("div", {
								className: "loading-state",
								children: [
									/* @__PURE__ */ (0, J.jsx)(ag, {
										size: 18,
										className: "spin"
									}),
									" ",
									r("common.loading")
								]
							}) : null,
							!D && !L.length ? /* @__PURE__ */ (0, J.jsx)(W_, { label: a.length ? r("common.noStoriesFilter") : r("common.noStories") }) : null,
							L.map((e) => {
								let t = Q(e.jira_key || e.story), n = Q(e.title, e.story);
								return /* @__PURE__ */ (0, J.jsxs)("button", {
									className: `observatory-story ${s === e.story ? "selected" : ""}`,
									onClick: () => ge(String(e.story)),
									children: [
										/* @__PURE__ */ (0, J.jsxs)("div", {
											className: "observatory-story-copy",
											children: [/* @__PURE__ */ (0, J.jsx)("span", {
												className: "observatory-key",
												children: t
											}), /* @__PURE__ */ (0, J.jsx)("span", {
												className: "observatory-story-title",
												children: n
											})]
										}),
										/* @__PURE__ */ (0, J.jsx)(c_, {
											date: String(e.updatedAt || ""),
											assignee: String(e.assignee || "")
										}),
										/* @__PURE__ */ (0, J.jsx)(l_, {
											business: String(e.businessStatus || "draft"),
											technical: String(e.technicalStatus || "draft")
										})
									]
								}, e.story);
							})
						]
					})
				]
			}),
			/* @__PURE__ */ (0, J.jsx)("section", {
				className: "observatory-detail panel",
				children: s ? /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "observatory-header",
					children: [/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "observatory-title-row",
						children: [/* @__PURE__ */ (0, J.jsx)("h2", { children: p ? /* @__PURE__ */ (0, J.jsxs)("a", {
							className: "observatory-heading-link",
							href: p,
							target: "_blank",
							rel: "noreferrer",
							children: [
								/* @__PURE__ */ (0, J.jsx)("span", {
									className: "observatory-key",
									children: be
								}),
								/* @__PURE__ */ (0, J.jsx)("span", {
									className: "observatory-heading-title",
									children: xe
								}),
								/* @__PURE__ */ (0, J.jsx)(qh, { size: 12 })
							]
						}) : /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [/* @__PURE__ */ (0, J.jsx)("span", {
							className: "observatory-key",
							children: be
						}), /* @__PURE__ */ (0, J.jsx)("span", {
							className: "observatory-heading-title",
							children: xe
						})] }) }), /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "panel-actions observatory-actions",
							children: [pe && /* @__PURE__ */ (0, J.jsxs)("button", {
								type: "button",
								className: "button secondary",
								disabled: se || k,
								onClick: _e,
								children: [/* @__PURE__ */ (0, J.jsx)(cg, { size: 14 }), r("action.startDelivery")]
							}), /* @__PURE__ */ (0, J.jsxs)("button", {
								type: "button",
								className: `button primary${A ? " is-busy" : ""}`,
								disabled: !de || A || k,
								onClick: () => void ye(),
								children: [A ? /* @__PURE__ */ (0, J.jsx)(ag, {
									size: 14,
									className: "spin"
								}) : /* @__PURE__ */ (0, J.jsx)(ug, { size: 14 }), r(A ? "common.saving" : "common.save")]
							})]
						})]
					}), /* @__PURE__ */ (0, J.jsx)("div", {
						className: "observatory-subheader",
						children: /* @__PURE__ */ (0, J.jsx)(o_, {
							business: h || "draft",
							technical: _ || "draft"
						})
					})]
				}), k ? /* @__PURE__ */ (0, J.jsxs)("div", {
					className: "loading-state",
					children: [
						/* @__PURE__ */ (0, J.jsx)(ag, {
							size: 20,
							className: "spin"
						}),
						" ",
						r("common.loading"),
						" Story…"
					]
				}) : /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "observatory-doc-tabs",
					role: "tablist",
					children: [/* @__PURE__ */ (0, J.jsx)("button", {
						type: "button",
						role: "tab",
						"aria-selected": T === "story",
						className: T === "story" ? "active" : "",
						onClick: () => E("story"),
						children: r("label.story")
					}), /* @__PURE__ */ (0, J.jsxs)("button", {
						type: "button",
						role: "tab",
						"aria-selected": T === "plan",
						className: T === "plan" ? "active" : "",
						onClick: () => E("plan"),
						children: [r("label.technical"), " plan"]
					})]
				}), T === "story" ? /* @__PURE__ */ (0, J.jsx)(D_, {
					value: y,
					onChange: b
				}, `${s || "none"}-story`) : /* @__PURE__ */ (0, J.jsx)(D_, {
					value: x,
					onChange: S
				}, `${s || "none"}-plan`)] })] }) : /* @__PURE__ */ (0, J.jsx)(W_, { label: r("common.selectStory") })
			}),
			ie > 0 && /* @__PURE__ */ (0, J.jsx)(ev, {
				stories: fe,
				value: ae,
				onChange: oe,
				step: ie === 1 ? 1 : 2,
				busy: se,
				error: le,
				onClose: () => {
					se || F(0);
				},
				onContinue: () => F(2),
				onConfirm: () => void ve()
			})
		]
	});
}
function iv({ jiraKey: e, title: t }) {
	let { t: n } = Z();
	return /* @__PURE__ */ (0, J.jsx)("span", {
		className: "story-reference",
		children: t ? /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [/* @__PURE__ */ (0, J.jsx)("code", { children: Q(e) }), /* @__PURE__ */ (0, J.jsx)("span", {
			className: "story-reference-title",
			children: t
		})] }) : /* @__PURE__ */ (0, J.jsx)("code", { children: Q(e, n("common.noData")) })
	});
}
function av({ stages: e, deliveryStatus: t, currentStep: n, startedAt: r, finishedAt: i, remediation: a, now: o, onStageClick: s }) {
	let { t: c } = Z(), l = /completed|dev_done|pr_open/i.test(t), u = /stopped from dashboard/i.test(String(n || "")), d = a?.status === "in_progress", f = d ? `${a.attempt}/${a.max_attempts}` : "", p = e.map((e) => {
		let t = String(e.status || "pending").toLowerCase();
		return l || t === "completed" ? "completed" : /running|progress/.test(t) ? "running" : u && /fail|block/.test(t) ? "stopped" : /fail|block/.test(t) ? "failed" : "pending";
	}).reduce((e, t) => e + (t === "completed" ? 1 : t === "running" ? .5 : 0), 0), m = e.length > 1 ? Math.max(0, Math.min(100, (p - 1) / (e.length - 1) * 100)) : 100;
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "delivery-flow",
		children: [/* @__PURE__ */ (0, J.jsxs)("div", {
			className: "flow-heading",
			children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsxs)("span", {
				className: "flow-title",
				children: [c("nav.delivery"), " Flow"]
			}), d && /* @__PURE__ */ (0, J.jsxs)("strong", {
				className: "remediation-alert",
				children: [
					/* @__PURE__ */ (0, J.jsx)(lg, { size: 13 }),
					"Verification failed · Remediation retry ",
					f
				]
			})] }), /* @__PURE__ */ (0, J.jsxs)("p", { children: [r ? c("label.startedAt", { value: $g(r) }) : c("label.notStarted"), i ? ` · ${c("label.finishedAtValue", { value: $g(i) })}` : ""] })]
		}), /* @__PURE__ */ (0, J.jsxs)("div", {
			className: "flow-track-wrap",
			children: [/* @__PURE__ */ (0, J.jsx)("span", {
				className: "flow-track",
				children: /* @__PURE__ */ (0, J.jsx)("i", { style: { width: `${m}%` } })
			}), /* @__PURE__ */ (0, J.jsx)("ol", {
				className: "flow-steps",
				style: { "--flow-count": e.length },
				children: e.map((e, t) => {
					let n = String(e.status || "pending").toLowerCase(), r = l || n === "completed" ? "completed" : /running|progress/.test(n) ? "running" : u && /fail|block/.test(n) ? "stopped" : /fail|block/.test(n) ? "failed" : "pending", i = r === "running" ? e_(e.active_started_at || e.started_at, new Date(o).toISOString()) : e.duration || "Pending", a = Array.isArray(e.attempts) && e.attempts.length > 1 ? ` · ${e.attempts.length} attempts` : "", p = r === "stopped" ? c("label.stopped") : d && r === "running" && ["implement", "verification"].includes(e.id) ? `Retry ${f} · ${i}` : d && e.id === "verification" && r === "failed" ? `Failed · remediation ${f}` : r === "failed" ? c("label.needsAttentionState") : `${i}${a}`;
					return /* @__PURE__ */ (0, J.jsx)("li", {
						className: `flow-step ${r}`,
						children: /* @__PURE__ */ (0, J.jsxs)("button", {
							className: "flow-stage-button",
							onClick: () => s(e),
							children: [/* @__PURE__ */ (0, J.jsx)("span", {
								className: "flow-marker",
								children: r === "completed" ? "✓" : r === "running" ? /* @__PURE__ */ (0, J.jsx)("span", { className: "pulse-dot" }) : t + 1
							}), /* @__PURE__ */ (0, J.jsxs)("span", {
								className: "flow-copy",
								children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: Q(e.label) }), /* @__PURE__ */ (0, J.jsx)("span", { children: p })]
							})]
						})
					}, `${e.label}-${t}`);
				})
			})]
		})]
	});
}
function ov({ stage: e, content: t, error: n, loading: r, live: i = !1, onClose: a }) {
	let { t: o } = Z(), s = (0, I.useRef)(null);
	return (0, I.useEffect)(() => {
		i && s.current && (s.current.scrollTop = s.current.scrollHeight);
	}, [t, i]), /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: a,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal delivery-log-modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": `${e.label} ${o("label.log")}`,
			onMouseDown: (e) => e.stopPropagation(),
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "delivery-log-header",
				children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [
					/* @__PURE__ */ (0, J.jsx)("span", { children: e.label }),
					/* @__PURE__ */ (0, J.jsxs)("strong", { children: [e.duration || "—", i && /* @__PURE__ */ (0, J.jsxs)("em", {
						className: "live-log",
						children: [/* @__PURE__ */ (0, J.jsx)("i", {}), o("common.live")]
					})] }),
					/* @__PURE__ */ (0, J.jsx)("p", { children: e.detail || o("label.noLog") }),
					Array.isArray(e.attempts) && e.attempts.length > 0 && /* @__PURE__ */ (0, J.jsx)("small", {
						className: "stage-attempts",
						children: e.attempts.map((e) => o("common.attempt", {
							number: e.number,
							duration: e.duration
						})).join(" · ")
					})
				] }), /* @__PURE__ */ (0, J.jsx)("button", {
					className: "button secondary",
					onClick: a,
					children: o("common.close")
				})]
			}), /* @__PURE__ */ (0, J.jsx)("pre", {
				ref: s,
				className: "delivery-log-content",
				children: /* @__PURE__ */ (0, J.jsx)("code", { children: r && !t ? o("common.loading") : n || t })
			})]
		})
	});
}
function sv({ label: e, value: t }) {
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "fact",
		children: [/* @__PURE__ */ (0, J.jsx)("span", { children: e }), /* @__PURE__ */ (0, J.jsx)("strong", { children: t })]
	});
}
function cv({ items: e }) {
	let { t } = Z();
	return e.length ? /* @__PURE__ */ (0, J.jsx)("span", {
		className: "pr-links",
		children: e.map((e, n) => /* @__PURE__ */ (0, J.jsxs)("a", {
			href: e.url,
			target: "_blank",
			rel: "noreferrer",
			children: [
				Q(e.repository, t("action.pullRequest")),
				String(e.url || "").match(/\/(\d+)\/?$/) ? ` #${String(e.url).match(/\/(\d+)\/?$/)?.[1]}` : "",
				/* @__PURE__ */ (0, J.jsx)(qh, { size: 12 })
			]
		}, `${e.url}-${n}`))
	}) : /* @__PURE__ */ (0, J.jsx)(J.Fragment, { children: "—" });
}
function lv({ checks: e, onClick: t }) {
	let { t: n } = Z(), r = e.filter((e) => e.status === "failed").length, i = e.filter((e) => e.status === "passed").length;
	return e.length ? /* @__PURE__ */ (0, J.jsx)("button", {
		className: `check-summary ${r ? "failed" : ""}`,
		title: n("label.verification"),
		onClick: t,
		children: r ? n("label.checksFailed", { count: r }) : n("label.checksPassed", { count: `${i}/${e.length}` })
	}) : /* @__PURE__ */ (0, J.jsx)(J.Fragment, { children: "—" });
}
function uv({ checks: e, onClose: t }) {
	let { t: n } = Z();
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: t,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal verification-modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": n("label.verification"),
			onMouseDown: (e) => e.stopPropagation(),
			children: [/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "delivery-log-header",
				children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [
					/* @__PURE__ */ (0, J.jsx)("span", { children: n("label.verification") }),
					/* @__PURE__ */ (0, J.jsx)("strong", { children: n("label.checksTitle") }),
					/* @__PURE__ */ (0, J.jsxs)("p", { children: [
						n("label.checksPassed", { count: e.filter((e) => e.status === "passed").length }),
						" · ",
						n("label.checksFailed", { count: e.filter((e) => e.status === "failed").length }),
						" · ",
						n("label.checksSkipped", { count: e.filter((e) => e.status === "skipped").length })
					] })
				] }), /* @__PURE__ */ (0, J.jsx)("button", {
					className: "button secondary",
					onClick: t,
					children: n("common.close")
				})]
			}), /* @__PURE__ */ (0, J.jsx)("div", {
				className: "verification-list",
				children: e.map((e, t) => /* @__PURE__ */ (0, J.jsxs)("article", {
					className: "verification-check",
					children: [
						/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: Q(e.label) }), /* @__PURE__ */ (0, J.jsx)("span", { children: Q(e.repository, n("common.workspace")) })] }),
						/* @__PURE__ */ (0, J.jsx)(a_, { value: e.status }),
						/* @__PURE__ */ (0, J.jsx)("p", { children: Q(e.summary, n("label.noSummary")) }),
						e.command && /* @__PURE__ */ (0, J.jsx)("code", { children: e.command })
					]
				}, `${e.repository}-${e.id}-${t}`))
			})]
		})
	});
}
var dv = {
	"01-role-and-mission.md": {
		title: "Mission",
		description: "Scope, role, and review posture",
		icon: hg
	},
	"02-pipeline.md": {
		title: "Pipeline",
		description: "End-to-end scan sequence",
		icon: bg
	},
	"03-configuration.md": {
		title: "Configuration",
		description: "Workspace and runtime inputs",
		icon: pg
	},
	"04-workspace-and-worktrees.md": {
		title: "Worktrees",
		description: "Repository isolation and refresh",
		icon: Qh
	},
	"05-review-only-mode.md": {
		title: "Review mode",
		description: "Lightweight validation boundaries",
		icon: dg
	},
	"06-issue-registry.md": {
		title: "Issue registry",
		description: "Finding persistence and status",
		icon: Vh
	},
	"07-error-handling.md": {
		title: "Error handling",
		description: "Failure recording and recovery",
		icon: Uh
	},
	"08-github-pr-and-git.md": {
		title: "Git and PR",
		description: "Branch, commit, and PR controls",
		icon: Qh
	},
	"09-severity-guideline.md": {
		title: "Severity",
		description: "Finding classification policy",
		icon: Vh
	},
	"10-findings-and-auto-fix.md": {
		title: "Findings",
		description: "Review output and safe fixes",
		icon: Gh
	},
	"11-output-contract.md": {
		title: "Output",
		description: "Structured result contract",
		icon: Xh
	},
	"12-secrets-and-safety.md": {
		title: "Safety",
		description: "Secret redaction and boundaries",
		icon: mg
	},
	"13-console-summary.md": {
		title: "Summary",
		description: "Console and report output",
		icon: Hh
	},
	"01-role.md": {
		title: "Delivery role",
		description: "Delivery agent scope",
		icon: hg
	},
	"02-workspace.md": {
		title: "Context",
		description: "Story, docs, and workspace inputs",
		icon: Qh
	},
	"03-implementation.md": {
		title: "Implementation",
		description: "Code changes and verification",
		icon: Gh
	},
	"04-output-contract.md": {
		title: "Outcome",
		description: "PR, JIRA, and result record",
		icon: Hh
	},
	"03-jira-context.md": {
		title: "Jira context",
		description: "Primary, related, and keyword context",
		icon: ng
	},
	"04-repository-scope.md": {
		title: "Repository scope",
		description: "Registered repository and worktree rules",
		icon: Qh
	},
	"05-patch-implementation.md": {
		title: "Implementation",
		description: "Minimal Bug or copy change",
		icon: Gh
	},
	"06-self-check.md": {
		title: "Self-check",
		description: "Focused validation evidence",
		icon: Hh
	},
	"07-blocked-question.md": {
		title: "Blocked question",
		description: "One answerable human question",
		icon: Wh
	},
	"08-git-and-publish.md": {
		title: "Git handoff",
		description: "Agent output and publish boundaries",
		icon: Qh
	},
	"09-output-contract.md": {
		title: "Output contract",
		description: "Structured patch result",
		icon: Xh
	},
	"10-secrets-and-safety.md": {
		title: "Safety",
		description: "Secrets and change boundaries",
		icon: mg
	},
	"11-console-summary.md": {
		title: "Summary",
		description: "Concise Agent handoff",
		icon: Hh
	},
	"coding-guideline.md": {
		title: "Code standard",
		description: "Repository-level coding guidance",
		icon: Xh
	}
};
function fv(e) {
	return dv[e.path] || {
		title: e.path.replace(/\.md$/, "").replace(/^\d+-/, ""),
		description: "Prompt fragment",
		icon: Xh
	};
}
function pv(e, t) {
	let n = e.path;
	return t === "delivery" ? [
		"01-role.md",
		"02-workspace.md",
		"coding-guideline.md"
	].includes(n) ? "Inputs & Governance" : n === "03-implementation.md" ? "Implementation" : "Delivery Outputs" : t === "patch" ? [
		"01-role-and-mission.md",
		"03-jira-context.md",
		"04-repository-scope.md",
		"10-secrets-and-safety.md"
	].includes(n) ? "Inputs & Governance" : [
		"02-pipeline.md",
		"05-patch-implementation.md",
		"06-self-check.md"
	].includes(n) ? "Patch Execution" : ["07-blocked-question.md", "08-git-and-publish.md"].includes(n) ? "Operational Controls" : "Patch Outputs" : [
		"01-role-and-mission.md",
		"03-configuration.md",
		"04-workspace-and-worktrees.md",
		"12-secrets-and-safety.md"
	].includes(n) ? "Inputs & Governance" : [
		"02-pipeline.md",
		"05-review-only-mode.md",
		"09-severity-guideline.md",
		"10-findings-and-auto-fix.md"
	].includes(n) ? "Review Execution" : [
		"06-issue-registry.md",
		"07-error-handling.md",
		"08-github-pr-and-git.md"
	].includes(n) ? "Operational Controls" : "Delivery Outputs";
}
function mv(e) {
	return e === "delivery" ? [
		{
			title: "Trigger",
			eyebrow: "ENTRY",
			layers: [],
			scripts: [{
				name: "delivery_scheduler.py",
				description: "Find an approved, eligible story"
			}, {
				name: "prepare_delivery_run.py",
				description: "Create the run record"
			}]
		},
		{
			title: "Context",
			eyebrow: "GROUNDING",
			layers: ["Inputs & Governance"],
			scripts: [{
				name: "capture_jira_context.py",
				description: "Read story, comments, and media"
			}, {
				name: "compose_delivery_prompt.py",
				description: "Assemble the agent context"
			}]
		},
		{
			title: "Implement",
			eyebrow: "AGENT",
			layers: ["Implementation"],
			scripts: [{
				name: "run-delivery.sh",
				description: "Execute in isolated worktrees"
			}]
		},
		{
			title: "Verify & recover",
			eyebrow: "CONTROL",
			layers: [],
			scripts: [{
				name: "run_delivery_verification.py",
				description: "Compile, test, and inspect"
			}, {
				name: "prepare_delivery_remediation.py",
				description: "Prepare a bounded retry"
			}]
		},
		{
			title: "Publish",
			eyebrow: "OUTCOME",
			layers: ["Delivery Outputs"],
			scripts: [{
				name: "finalize_delivery.py",
				description: "Commit, PR, JIRA, and notification"
			}]
		}
	] : e === "patch" ? [
		{
			title: "Capture",
			eyebrow: "ENTRY",
			layers: [],
			scripts: [{
				name: "patch_scheduler.py",
				description: "Find one eligible Task or Bug"
			}]
		},
		{
			title: "Context",
			eyebrow: "GROUNDING",
			layers: ["Inputs & Governance"],
			scripts: [{
				name: "capture_patch_context.py",
				description: "Read the Jira story neighborhood"
			}, {
				name: "compose_patch_prompt.py",
				description: "Assemble bounded patch context"
			}]
		},
		{
			title: "Patch",
			eyebrow: "AGENT",
			layers: ["Patch Execution"],
			scripts: [{
				name: "run-patch.sh",
				description: "Run in an isolated patch worktree"
			}]
		},
		{
			title: "Control",
			eyebrow: "SAFETY",
			layers: ["Operational Controls"],
			scripts: [{
				name: "finalize_patch.py",
				description: "Self-check, commit, and publish"
			}]
		},
		{
			title: "Outcome",
			eyebrow: "HANDOFF",
			layers: ["Patch Outputs"],
			scripts: []
		}
	] : [
		{
			title: "Trigger",
			eyebrow: "ENTRY",
			layers: [],
			scripts: [{
				name: "run-scan.sh",
				description: "Start a scheduled or manual scan"
			}]
		},
		{
			title: "Context",
			eyebrow: "GROUNDING",
			layers: ["Inputs & Governance"],
			scripts: [{
				name: "prepare_scan_worktrees.py",
				description: "Refresh isolated repository views"
			}, {
				name: "compose_scan_prompt.py",
				description: "Assemble review context"
			}]
		},
		{
			title: "Review",
			eyebrow: "AGENT",
			layers: ["Review Execution"],
			scripts: []
		},
		{
			title: "Control & remediate",
			eyebrow: "CONTROL",
			layers: ["Operational Controls"],
			scripts: [{
				name: "auto_fix_sync.py",
				description: "Apply and re-check safe fixes"
			}]
		},
		{
			title: "Report",
			eyebrow: "OUTCOME",
			layers: ["Delivery Outputs"],
			scripts: [{
				name: "render-report-and-notify.py",
				description: "HTML, PDF, dashboard, and Feishu"
			}]
		}
	];
}
function hv({ data: e, project: t, interact: n, notify: r }) {
	let { t: i } = Z(), a = e.interactive?.prompts || [], [o, s] = (0, I.useState)("scan"), [c, l] = (0, I.useState)(null), [u, d] = (0, I.useState)(""), [f, p] = (0, I.useState)(!1), [m, h] = (0, I.useState)({
		x: 0,
		y: 0,
		scale: 1
	}), [g, _] = (0, I.useState)(!1), v = (0, I.useRef)(null), y = (0, I.useRef)(null), b = a.filter((e) => e.mode === o), x = async (e) => {
		l(e);
		try {
			let n = await i_(`/api/prompt?mode=${encodeURIComponent(e.mode)}&path=${encodeURIComponent(e.path)}`, t);
			d(n.content);
		} catch (e) {
			r(e instanceof Error ? e.message : "Unable to load prompt", "error");
		}
	}, S = async () => {
		if (!(!c || f)) {
			p(!0);
			try {
				await n("/api/prompt", {
					mode: c.mode,
					path: c.path,
					content: u
				}, "Prompt saved");
			} finally {
				p(!1);
			}
		}
	}, C = (e) => {
		s(e), l(null), d(""), h({
			x: 0,
			y: 0,
			scale: 1
		});
	};
	(0, I.useEffect)(() => {
		if (!g) return;
		let e = (e) => {
			e.key === "Escape" && _(!1);
		};
		return window.addEventListener("keydown", e), () => window.removeEventListener("keydown", e);
	}, [g]);
	let w = (0, I.useCallback)((e) => {
		e.preventDefault(), e.ctrlKey || e.metaKey ? h((t) => ({
			...t,
			scale: Math.max(.65, Math.min(1.55, t.scale * (e.deltaY > 0 ? .975 : 1.025)))
		})) : h((t) => ({
			...t,
			x: t.x - e.deltaX,
			y: t.y - e.deltaY
		}));
	}, []);
	(0, I.useEffect)(() => {
		let e = y.current;
		if (e) return e.addEventListener("wheel", w, { passive: !1 }), () => e.removeEventListener("wheel", w);
	}, [w]);
	let T = (e) => {
		e.target.closest("button,a,textarea,input") || (v.current = {
			id: e.pointerId,
			x: e.clientX,
			y: e.clientY
		}, e.currentTarget.setPointerCapture(e.pointerId));
	}, E = (e) => {
		if (!v.current || v.current.id !== e.pointerId) return;
		let t = e.clientX - v.current.x, n = e.clientY - v.current.y;
		v.current = {
			...v.current,
			x: e.clientX,
			y: e.clientY
		}, h((e) => ({
			...e,
			x: e.x + t,
			y: e.y + n
		}));
	}, D = (e) => {
		v.current?.id === e.pointerId && (v.current = null);
	}, O = mv(o);
	return /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [
		/* @__PURE__ */ (0, J.jsxs)("div", {
			className: "workflow-mode-switch",
			role: "tablist",
			children: [
				/* @__PURE__ */ (0, J.jsx)("button", {
					className: o === "scan" ? "active" : "",
					onClick: () => C("scan"),
					children: i("label.autoScan")
				}),
				/* @__PURE__ */ (0, J.jsx)("button", {
					className: o === "delivery" ? "active" : "",
					onClick: () => C("delivery"),
					children: i("label.autoDelivery")
				}),
				/* @__PURE__ */ (0, J.jsx)("button", {
					className: o === "patch" ? "active" : "",
					onClick: () => C("patch"),
					children: i("label.autoPatch")
				})
			]
		}),
		/* @__PURE__ */ (0, J.jsx)(k_, {
			title: i("heading.workflow", { feature: i(o === "scan" ? "label.autoScan" : o === "delivery" ? "label.autoDelivery" : "label.autoPatch") }),
			action: /* @__PURE__ */ (0, J.jsx)(O_, {
				label: i(g ? "action.exitFullscreen" : "action.viewFullscreen"),
				onClick: () => _((e) => !e),
				children: g ? /* @__PURE__ */ (0, J.jsx)(sg, { size: 14 }) : /* @__PURE__ */ (0, J.jsx)(og, { size: 14 })
			}),
			className: `workflow-panel ${g ? "workflow-panel-fullscreen" : ""}`,
			children: /* @__PURE__ */ (0, J.jsx)("div", {
				ref: y,
				className: "workflow-canvas workflow-viewport",
				onPointerDown: T,
				onPointerMove: E,
				onPointerUp: D,
				onPointerCancel: D,
				children: /* @__PURE__ */ (0, J.jsxs)("div", {
					className: "workflow-scale",
					style: { transform: `translate(${m.x}px, ${m.y}px) scale(${m.scale})` },
					children: [/* @__PURE__ */ (0, J.jsx)("div", {
						className: "workflow-columns",
						children: O.map((e, t) => {
							let n = b.filter((t) => e.layers.includes(pv(t, o))), r = [...e.scripts.map((e) => ({
								kind: "script",
								script: e
							})), ...n.map((e) => ({
								kind: "prompt",
								prompt: e
							}))];
							return /* @__PURE__ */ (0, J.jsxs)("section", {
								className: "workflow-column",
								children: [
									/* @__PURE__ */ (0, J.jsxs)("header", { children: [/* @__PURE__ */ (0, J.jsx)("span", { children: e.eyebrow }), /* @__PURE__ */ (0, J.jsx)("strong", { children: e.title })] }),
									/* @__PURE__ */ (0, J.jsx)("div", {
										className: "workflow-node-stack",
										children: r.map((e, n) => {
											let r = `${t + 1}.${n + 1}`;
											if (e.kind === "script") return /* @__PURE__ */ (0, J.jsxs)("article", {
												className: "workflow-node script-node",
												children: [
													/* @__PURE__ */ (0, J.jsx)(gg, { size: 14 }),
													/* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: e.script.name }), /* @__PURE__ */ (0, J.jsx)("small", { children: e.script.description })] }),
													/* @__PURE__ */ (0, J.jsxs)("em", { children: [/* @__PURE__ */ (0, J.jsx)("b", { children: r }), " SCRIPT"] })
												]
											}, e.script.name);
											let i = e.prompt, a = fv(i), o = a.icon;
											return /* @__PURE__ */ (0, J.jsxs)("button", {
												className: `workflow-node prompt-node ${c?.mode === i.mode && c.path === i.path ? "selected" : ""}`,
												onClick: () => void x(i),
												children: [
													/* @__PURE__ */ (0, J.jsx)(o, { size: 14 }),
													/* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: a.title }), /* @__PURE__ */ (0, J.jsx)("small", { children: a.description })] }),
													/* @__PURE__ */ (0, J.jsxs)("em", { children: [/* @__PURE__ */ (0, J.jsx)("b", { children: r }), " PROMPT"] })
												]
											}, `${i.mode}/${i.path}`);
										})
									}),
									t < O.length - 1 && /* @__PURE__ */ (0, J.jsx)("span", {
										className: "workflow-connector",
										"aria-hidden": "true"
									})
								]
							}, e.title);
						})
					}), /* @__PURE__ */ (0, J.jsxs)("div", {
						className: "workflow-retry",
						children: [/* @__PURE__ */ (0, J.jsx)(lg, { size: 14 }), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: o === "delivery" ? "Remediation retry" : o === "patch" ? "Blocked-question retry" : "Safe-fix re-review" }), /* @__PURE__ */ (0, J.jsx)("small", { children: o === "delivery" ? "Verification failure → prepare_delivery_remediation.py → implementation agent → verification" : o === "patch" ? "External Jira reply → capture context → rerun the complete patch flow" : "High-confidence finding → auto_fix_sync.py → focused validation → pull request" })] })]
					})]
				})
			})
		}),
		c && /* @__PURE__ */ (0, J.jsx)(gv, {
			item: c,
			content: u,
			saving: f,
			onChange: d,
			onClose: () => {
				f || (l(null), d(""));
			},
			onSave: () => void S()
		})
	] });
}
function gv({ item: e, content: t, saving: n, onChange: r, onClose: i, onSave: a }) {
	let { t: o } = Z(), s = fv(e), c = e.mode === "scan" ? o("label.autoScan") : e.mode === "delivery" ? o("label.autoDelivery") : o("label.autoPatch");
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: n ? void 0 : i,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal prompt-inspector-modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": `${s.title} prompt`,
			onMouseDown: (e) => e.stopPropagation(),
			children: [
				/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "prompt-inspector-header",
					children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [
						/* @__PURE__ */ (0, J.jsxs)("span", { children: [
							c,
							" ",
							o("label.prompt")
						] }),
						/* @__PURE__ */ (0, J.jsx)("strong", { children: s.title }),
						/* @__PURE__ */ (0, J.jsx)("code", { children: e.path })
					] }), /* @__PURE__ */ (0, J.jsx)("button", {
						className: "button secondary",
						disabled: n,
						onClick: i,
						children: o("common.close")
					})]
				}),
				/* @__PURE__ */ (0, J.jsx)("div", {
					className: "prompt-inspector-body",
					children: /* @__PURE__ */ (0, J.jsxs)("div", {
						className: "markdown-workbench",
						children: [/* @__PURE__ */ (0, J.jsxs)("label", {
							className: "markdown-pane",
							children: [/* @__PURE__ */ (0, J.jsx)("span", { children: o("prompt.original") }), /* @__PURE__ */ (0, J.jsx)("textarea", {
								value: t,
								onChange: (e) => r(e.target.value),
								spellCheck: !1,
								disabled: n
							})]
						}), /* @__PURE__ */ (0, J.jsxs)("article", {
							className: "markdown-preview",
							children: [/* @__PURE__ */ (0, J.jsx)("span", { children: o("prompt.preview") }), /* @__PURE__ */ (0, J.jsx)(g_, { content: t })]
						})]
					})
				}),
				/* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
					className: "button",
					disabled: n,
					onClick: i,
					children: o("common.cancel")
				}), /* @__PURE__ */ (0, J.jsxs)("button", {
					className: `button primary${n ? " is-busy" : ""}`,
					disabled: n,
					onClick: a,
					children: [n ? /* @__PURE__ */ (0, J.jsx)(ag, {
						size: 14,
						className: "spin"
					}) : /* @__PURE__ */ (0, J.jsx)(ug, { size: 14 }), o(n ? "common.saving" : "action.savePrompt")]
				})] })
			]
		})
	});
}
function _v({ children: e }) {
	let { t } = Z();
	return /* @__PURE__ */ (0, J.jsxs)("details", {
		className: "field-help",
		children: [/* @__PURE__ */ (0, J.jsx)("summary", {
			"aria-label": t("common.explainSetting"),
			children: /* @__PURE__ */ (0, J.jsx)(Wh, { size: 13 })
		}), /* @__PURE__ */ (0, J.jsx)("span", {
			role: "tooltip",
			children: e
		})]
	});
}
function $({ label: e, help: t, children: n }) {
	return /* @__PURE__ */ (0, J.jsxs)("label", {
		className: "field",
		children: [/* @__PURE__ */ (0, J.jsxs)("span", {
			className: "field-label",
			children: [e, t && /* @__PURE__ */ (0, J.jsx)(_v, { children: t })]
		}), n]
	});
}
function vv({ options: e, value: t, onChange: n, markDirty: r }) {
	let { t: i } = Z(), a = (0, I.useRef)(null), [o, s] = (0, I.useState)(!1);
	(0, I.useEffect)(() => {
		let e = (e) => {
			a.current?.contains(e.target) || s(!1);
		}, t = (e) => {
			e.key === "Escape" && s(!1);
		};
		return document.addEventListener("pointerdown", e), document.addEventListener("keydown", t), () => {
			document.removeEventListener("pointerdown", e), document.removeEventListener("keydown", t);
		};
	}, []);
	let c = (e) => {
		n(t.includes(e) ? t.filter((t) => t !== e) : [...t, e]), r();
	}, l = t.length === 0 ? i("label.eligibleStatuses") : t.length === 1 ? t[0] : i("common.statusesSelected", { count: t.length });
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		ref: a,
		className: `status-picker ${o ? "is-open" : ""}`,
		children: [/* @__PURE__ */ (0, J.jsxs)("button", {
			type: "button",
			className: "status-picker-trigger",
			"aria-label": i("label.eligibleStatuses"),
			"aria-expanded": o,
			onClick: () => s((e) => !e),
			children: [/* @__PURE__ */ (0, J.jsx)("span", {
				className: `status-picker-summary ${t.length === 0 ? "placeholder" : ""}`,
				title: t.join(", "),
				children: l
			}), /* @__PURE__ */ (0, J.jsx)(zh, {
				size: 15,
				"aria-hidden": "true"
			})]
		}), o && /* @__PURE__ */ (0, J.jsxs)("div", {
			className: "status-picker-menu",
			role: "listbox",
			"aria-label": i("label.eligibleStatuses"),
			"aria-multiselectable": "true",
			children: [/* @__PURE__ */ (0, J.jsx)("div", {
				className: "status-picker-options",
				children: e.map((e) => {
					let n = t.includes(e);
					return /* @__PURE__ */ (0, J.jsxs)("button", {
						type: "button",
						role: "option",
						"aria-selected": n,
						className: `status-picker-option ${n ? "selected" : ""}`,
						onClick: () => c(e),
						children: [/* @__PURE__ */ (0, J.jsx)("span", {
							className: "status-picker-check",
							"aria-hidden": "true",
							children: n ? "✓" : ""
						}), /* @__PURE__ */ (0, J.jsx)("span", { children: e })]
					}, e);
				})
			}), /* @__PURE__ */ (0, J.jsxs)("footer", {
				className: "status-picker-footer",
				children: [/* @__PURE__ */ (0, J.jsx)("span", { children: i("common.selected", { count: t.length }) }), t.length > 0 && /* @__PURE__ */ (0, J.jsx)("button", {
					type: "button",
					onClick: () => {
						n([]), r();
					},
					children: i("common.clear")
				})]
			})]
		})]
	});
}
function yv({ label: e, value: t, onChange: n, markDirty: r }) {
	let { t: i } = Z(), a = Qg(t), o = Yg.some((e) => e.value === a), s = a || i("customModel.option"), [c, l] = (0, I.useState)(!1), u = () => l(!0);
	return /* @__PURE__ */ (0, J.jsxs)($, {
		label: e,
		help: i("customModel.help"),
		children: [
			/* @__PURE__ */ (0, J.jsxs)("div", {
				className: `model-select-row${o ? "" : " is-custom"}`,
				children: [/* @__PURE__ */ (0, J.jsxs)("select", {
					title: o ? void 0 : a,
					value: o ? a : Xg,
					onChange: (e) => {
						e.target.value === Xg ? u() : (n(e.target.value), r());
					},
					children: [Yg.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
						value: e.value,
						children: e.label
					}, e.value)), /* @__PURE__ */ (0, J.jsx)("option", {
						value: Xg,
						children: s
					})]
				}), !o && /* @__PURE__ */ (0, J.jsx)("span", {
					className: "custom-model-badge",
					children: i("customModel.badge")
				})]
			}),
			!o && /* @__PURE__ */ (0, J.jsx)("button", {
				type: "button",
				className: "custom-model-edit",
				onClick: u,
				children: i("customModel.edit")
			}),
			c && /* @__PURE__ */ (0, J.jsx)(bv, {
				label: e,
				value: t,
				onClose: () => l(!1),
				onConfirm: (e) => {
					n(e), r(), l(!1);
				}
			})
		]
	});
}
function bv({ label: e, value: t, onClose: n, onConfirm: r }) {
	let { t: i } = Z(), [a, o] = (0, I.useState)(t);
	return (0, I.useEffect)(() => {
		let e = (e) => {
			e.key === "Escape" && n();
		};
		return window.addEventListener("keydown", e), () => window.removeEventListener("keydown", e);
	}, [n]), /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: n,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal custom-model-modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-labelledby": "custom-model-title",
			onMouseDown: (e) => e.stopPropagation(),
			children: [
				/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "custom-model-header",
					children: [/* @__PURE__ */ (0, J.jsx)("strong", {
						id: "custom-model-title",
						children: i("customModel.enter")
					}), /* @__PURE__ */ (0, J.jsxs)("p", { children: [
						e,
						" · ",
						i("customModel.help")
					] })]
				}),
				/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "modal-body compact",
					children: [/* @__PURE__ */ (0, J.jsx)($, {
						label: i("customModel.id"),
						children: /* @__PURE__ */ (0, J.jsx)("input", {
							autoFocus: !0,
							value: a,
							placeholder: i("customModel.placeholder"),
							"aria-label": i("customModel.id"),
							onChange: (e) => o(e.target.value)
						})
					}), /* @__PURE__ */ (0, J.jsx)("p", {
						className: "modal-copy",
						children: i("customModel.copy")
					})]
				}),
				/* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
					type: "button",
					className: "button",
					onClick: n,
					children: i("common.cancel")
				}), /* @__PURE__ */ (0, J.jsx)("button", {
					type: "button",
					className: "button primary",
					disabled: !a.trim(),
					onClick: () => {
						let e = a.trim();
						e && r(e);
					},
					children: i("common.confirm")
				})] })
			]
		})
	});
}
function xv({ data: e, interact: t }) {
	let { t: n } = Z(), r = e.interactive?.workspace || {}, [i, a] = (0, I.useState)(r.repositories || []), [o, s] = (0, I.useState)(!1), [c, l] = (0, I.useState)(!1), [u, d] = (0, I.useState)(null), [f, p] = (0, I.useState)(!1), [m, h] = (0, I.useState)("all");
	(0, I.useEffect)(() => {
		o || a(r.repositories || []);
	}, [r.repositories, o]);
	let g = (e, t) => {
		s(!0), a((n) => n.map((n, r) => r === e ? {
			...n,
			...t
		} : n));
	}, _ = (e) => (e.delivery_steps || []).map((e) => Array.isArray(e.command) ? e.command.join(" ") : "").filter(Boolean).join("\n"), v = (e) => {
		let t = e.verification && typeof e.verification == "object" ? e.verification : {};
		return {
			mode: [
				"auto",
				"custom",
				"skip"
			].includes(String(t.mode || "")) ? String(t.mode) : _(e) ? "custom" : "auto",
			compile: t.compile !== !1,
			tests: t.tests !== !1
		};
	}, y = (e) => ({
		scan: { allow_auto_fix: e.automation?.scan?.allow_auto_fix ?? e.allow_auto_fix !== !1 },
		delivery: { enabled: e.automation?.delivery?.enabled !== !1 },
		patch: { enabled: e.automation?.patch?.enabled ?? !0 }
	}), b = (e, t, n) => {
		s(!0), a((r) => r.map((r, i) => i === e ? {
			...r,
			automation: {
				...y(r),
				[t]: {
					...y(r)[t],
					...n
				}
			}
		} : r));
	}, x = (e, t) => {
		s(!0), a((n) => n.map((n, r) => r === e ? {
			...n,
			verification: {
				...v(n),
				...t
			}
		} : n));
	}, S = async () => {
		if (!(!o || c)) {
			l(!0);
			try {
				await t("/api/repositories", { repositories: i }, "Repository governance saved") && (s(!1), d(null));
			} finally {
				l(!1);
			}
		}
	}, C = (e) => {
		let t = e.health || {}, n = [];
		return t.git_status === "changes" && n.push("Uncommitted changes"), t.git_status === "behind" && n.push("Branch behind remote"), t.git_status === "diverged" && n.push("Branch diverged"), t.sync_status === "behind" && n.push("Sync behind remote"), t.sync_status === "diverged" && n.push("Sync diverged"), Array.from(new Set(n));
	}, w = (e) => `${e.java_version ? `Java ${e.java_version}` : e.node_version ? `Node.js ${e.node_version}` : e.language || "Generic"} · ${e.build_tools?.join(", ") || "No build tool detected"}`, T = (e) => {
		let t = Q(e, n("status.notSet"));
		return /* @__PURE__ */ (0, J.jsx)("span", {
			className: "repository-fact-value",
			"data-tooltip": t,
			title: t,
			tabIndex: 0,
			"aria-label": t,
			children: /* @__PURE__ */ (0, J.jsx)("code", { children: t })
		});
	}, E = i.filter((e) => C(e).length > 0).length, D = i.filter((e) => y(e).scan.allow_auto_fix).length, O = i.filter((e) => y(e).delivery.enabled).length, k = i.filter((e) => y(e).patch.enabled).length, ee = i.filter((e) => m === "all" || m === "patch" && y(e).patch.enabled || m === "attention" && C(e).length > 0), A = u ? i.find((e) => e.name === u) : null, j = A ? i.indexOf(A) : -1, M = A?.health || {}, N = A ? y(A) : null, P = A ? v(A) : null;
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "repository-page",
		children: [
			/* @__PURE__ */ (0, J.jsxs)(k_, {
				title: n("common.repositoryGovernance"),
				action: /* @__PURE__ */ (0, J.jsx)("button", {
					className: "button secondary",
					onClick: () => p(!0),
					children: n("common.addRepository")
				}),
				children: [
					/* @__PURE__ */ (0, J.jsx)("div", {
						className: "repository-intro",
						children: n("common.repositoryIntro")
					}),
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "repository-overview",
						children: [
							/* @__PURE__ */ (0, J.jsx)(sv, {
								label: n("common.all"),
								value: i.length
							}),
							/* @__PURE__ */ (0, J.jsx)(sv, {
								label: n("label.needsAttention"),
								value: E
							}),
							/* @__PURE__ */ (0, J.jsx)(sv, {
								label: n("label.autoScan"),
								value: `${D}/${i.length} ${n("common.enabled")}`
							}),
							/* @__PURE__ */ (0, J.jsx)(sv, {
								label: n("label.autoDelivery"),
								value: `${O}/${i.length} ${n("common.enabled")}`
							}),
							/* @__PURE__ */ (0, J.jsx)(sv, {
								label: n("label.autoPatch"),
								value: `${k}/${i.length} ${n("common.enabled")}`
							})
						]
					}),
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "repository-filters",
						children: [
							/* @__PURE__ */ (0, J.jsxs)("button", {
								className: m === "all" ? "active" : "",
								onClick: () => h("all"),
								children: [
									n("common.all"),
									" (",
									i.length,
									")"
								]
							}),
							/* @__PURE__ */ (0, J.jsxs)("button", {
								className: m === "attention" ? "active" : "",
								onClick: () => h("attention"),
								children: [
									n("label.needsAttention"),
									" (",
									E,
									")"
								]
							}),
							/* @__PURE__ */ (0, J.jsxs)("button", {
								className: m === "patch" ? "active" : "",
								onClick: () => h("patch"),
								children: [
									n("label.autoPatch"),
									" ",
									n("common.enabled"),
									" (",
									k,
									")"
								]
							})
						]
					}),
					m === "attention" && /* @__PURE__ */ (0, J.jsxs)("div", {
						className: "repository-filter-note",
						children: [/* @__PURE__ */ (0, J.jsx)(Vh, {
							size: 14,
							"aria-hidden": "true"
						}), /* @__PURE__ */ (0, J.jsx)("span", { children: n("common.attentionNote") })]
					}),
					/* @__PURE__ */ (0, J.jsx)("div", {
						className: "repository-list",
						children: /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "repository-grid",
							children: [ee.map((e) => {
								let t = e.health || {}, n = y(e);
								return /* @__PURE__ */ (0, J.jsx)("article", {
									className: "repository-card",
									children: /* @__PURE__ */ (0, J.jsxs)("button", {
										type: "button",
										className: "repository-card-button",
										onClick: () => d(e.name),
										"aria-label": `Edit ${e.name || "repository"}`,
										children: [/* @__PURE__ */ (0, J.jsxs)("div", {
											className: "repository-card-heading",
											children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: e.name || "Unnamed repository" }), /* @__PURE__ */ (0, J.jsx)("span", { children: w(t) })] }), /* @__PURE__ */ (0, J.jsx)(Bh, {
												size: 16,
												"aria-hidden": "true"
											})]
										}), /* @__PURE__ */ (0, J.jsxs)("div", {
											className: "repository-card-bottom",
											children: [/* @__PURE__ */ (0, J.jsxs)("div", {
												className: "repository-card-permissions",
												children: [
													/* @__PURE__ */ (0, J.jsxs)("span", {
														className: n.scan.allow_auto_fix ? "enabled" : "disabled",
														children: ["Auto Scan ", n.scan.allow_auto_fix ? "enabled" : "disabled"]
													}),
													/* @__PURE__ */ (0, J.jsxs)("span", {
														className: n.delivery.enabled ? "enabled" : "disabled",
														children: ["Auto Delivery ", n.delivery.enabled ? "enabled" : "disabled"]
													}),
													/* @__PURE__ */ (0, J.jsxs)("span", {
														className: n.patch.enabled ? "enabled" : "disabled",
														children: ["Auto Patch ", n.patch.enabled ? "enabled" : "disabled"]
													})
												]
											}), /* @__PURE__ */ (0, J.jsxs)("span", {
												className: "repository-card-branch",
												children: [/* @__PURE__ */ (0, J.jsx)(Qh, {
													size: 12,
													"aria-hidden": "true"
												}), e.default_branch || "main"]
											})]
										})]
									})
								}, e.name);
							}), ee.length === 0 && /* @__PURE__ */ (0, J.jsx)(W_, { label: n("common.noData") })]
						})
					})
				]
			}),
			A && j >= 0 && N && P && /* @__PURE__ */ (0, J.jsx)("div", {
				className: "modal-backdrop repository-config-backdrop",
				role: "presentation",
				onMouseDown: () => d(null),
				children: /* @__PURE__ */ (0, J.jsxs)("section", {
					className: "modal repository-config-modal",
					role: "dialog",
					"aria-modal": "true",
					"aria-labelledby": "repository-config-title",
					onMouseDown: (e) => e.stopPropagation(),
					children: [
						/* @__PURE__ */ (0, J.jsxs)("header", {
							className: "repository-config-header",
							children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [
								/* @__PURE__ */ (0, J.jsx)("strong", {
									id: "repository-config-title",
									children: A.name || n("common.unnamedRepository")
								}),
								/* @__PURE__ */ (0, J.jsx)("span", { children: n("common.repositoryConfiguration") }),
								/* @__PURE__ */ (0, J.jsxs)("p", { children: [
									M.language || n("common.generic"),
									" · ",
									M.build_tools?.join(", ") || n("common.noBuildTool"),
									" · ",
									A.default_branch || "main"
								] })
							] }), /* @__PURE__ */ (0, J.jsx)(O_, {
								label: n("common.close"),
								onClick: () => d(null),
								children: /* @__PURE__ */ (0, J.jsx)(xg, { size: 15 })
							})]
						}),
						/* @__PURE__ */ (0, J.jsx)("div", {
							className: "repository-config-body",
							children: /* @__PURE__ */ (0, J.jsxs)("div", {
								className: "repository-editor",
								children: [
									/* @__PURE__ */ (0, J.jsxs)("section", {
										className: "repository-section",
										children: [
											/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.identityConnection") }), /* @__PURE__ */ (0, J.jsx)("span", { children: n("common.identityConnectionHelp") })] }),
											/* @__PURE__ */ (0, J.jsxs)("div", {
												className: "repository-facts",
												children: [
													/* @__PURE__ */ (0, J.jsx)(sv, {
														label: n("common.localPath"),
														value: T(A.path)
													}),
													/* @__PURE__ */ (0, J.jsx)(sv, {
														label: n("common.remote"),
														value: T(M.remote_url || A.remote_url)
													}),
													/* @__PURE__ */ (0, J.jsx)(sv, {
														label: n("common.gitStatus"),
														value: /* @__PURE__ */ (0, J.jsx)(a_, { value: M.git_status || "unknown" })
													}),
													/* @__PURE__ */ (0, J.jsx)(sv, {
														label: n("common.branchSync"),
														value: /* @__PURE__ */ (0, J.jsx)(a_, { value: M.sync_status || "unknown" })
													})
												]
											}),
											/* @__PURE__ */ (0, J.jsx)("div", {
												className: "form-grid compact",
												children: /* @__PURE__ */ (0, J.jsx)($, {
													label: n("common.defaultBranch"),
													children: /* @__PURE__ */ (0, J.jsx)("select", {
														value: A.default_branch || "",
														onChange: (e) => g(j, { default_branch: e.target.value }),
														children: Array.from(new Set([A.default_branch, ...A.branches || []].filter(Boolean))).map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
															value: e,
															children: e
														}, e))
													})
												})
											})
										]
									}),
									/* @__PURE__ */ (0, J.jsxs)("section", {
										className: "repository-section",
										children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.runtimeBuild") }), /* @__PURE__ */ (0, J.jsx)("span", { children: n("common.runtimeBuildHelp") })] }), /* @__PURE__ */ (0, J.jsxs)("div", {
											className: "repository-facts",
											children: [
												/* @__PURE__ */ (0, J.jsx)(sv, {
													label: n("common.language"),
													value: M.language || "Generic"
												}),
												/* @__PURE__ */ (0, J.jsx)(sv, {
													label: n("common.java"),
													value: M.java_version ? `Java ${M.java_version}` : "Not detected"
												}),
												/* @__PURE__ */ (0, J.jsx)(sv, {
													label: n("common.node"),
													value: M.node_version ? `Node ${M.node_version}` : "Not detected"
												}),
												/* @__PURE__ */ (0, J.jsx)(sv, {
													label: n("common.buildTools"),
													value: M.build_tools?.join(", ") || "Not detected"
												})
											]
										})]
									}),
									/* @__PURE__ */ (0, J.jsxs)("section", {
										className: "repository-section",
										children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.automationPermissions") }), /* @__PURE__ */ (0, J.jsx)("span", { children: n("common.frontendDeliveryDisabled") })] }), /* @__PURE__ */ (0, J.jsxs)("div", {
											className: "repository-policy-grid",
											children: [
												/* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
													type: "checkbox",
													checked: N.scan.allow_auto_fix,
													onChange: (e) => b(j, "scan", { allow_auto_fix: e.target.checked })
												}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.autoScanFixes") }), /* @__PURE__ */ (0, J.jsx)("small", { children: n("common.autoScanFixesHelp") })] })] }),
												/* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
													type: "checkbox",
													checked: N.delivery.enabled,
													onChange: (e) => b(j, "delivery", { enabled: e.target.checked })
												}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.deliveryPermission") }), /* @__PURE__ */ (0, J.jsx)("small", { children: n("common.deliveryPermissionHelp") })] })] }),
												/* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
													type: "checkbox",
													checked: N.patch.enabled,
													onChange: (e) => b(j, "patch", { enabled: e.target.checked })
												}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.patchPermission") }), /* @__PURE__ */ (0, J.jsx)("small", { children: n("common.patchPermissionHelp") })] })] })
											]
										})]
									}),
									/* @__PURE__ */ (0, J.jsxs)("section", {
										className: "repository-section repository-verification-section",
										children: [
											/* @__PURE__ */ (0, J.jsxs)("div", {
												className: "repository-section-heading",
												children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.deliveryVerification") }), /* @__PURE__ */ (0, J.jsx)("span", { children: n("common.deliveryVerificationHelp") })]
											}),
											/* @__PURE__ */ (0, J.jsxs)("div", {
												className: "verification-group",
												children: [/* @__PURE__ */ (0, J.jsx)("span", {
													className: "verification-group-label",
													children: n("common.policy")
												}), /* @__PURE__ */ (0, J.jsxs)("div", {
													className: "verification-mode-grid",
													children: [/* @__PURE__ */ (0, J.jsxs)("label", {
														className: `verification-mode-card${P.mode === "skip" ? "" : " selected"}`,
														children: [/* @__PURE__ */ (0, J.jsx)("input", {
															type: "radio",
															name: `verification-mode-${A.name}`,
															checked: P.mode !== "skip",
															onChange: () => x(j, { mode: P.mode === "custom" ? "custom" : "auto" })
														}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.runVerification") }), /* @__PURE__ */ (0, J.jsx)("small", { children: n("common.runVerificationHelp") })] })]
													}), /* @__PURE__ */ (0, J.jsxs)("label", {
														className: `verification-mode-card${P.mode === "skip" ? " selected" : ""}`,
														children: [/* @__PURE__ */ (0, J.jsx)("input", {
															type: "radio",
															name: `verification-mode-${A.name}`,
															checked: P.mode === "skip",
															onChange: () => x(j, { mode: "skip" })
														}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.skipVerification") }), /* @__PURE__ */ (0, J.jsx)("small", { children: n("common.skipVerificationHelp") })] })]
													})]
												})]
											}),
											P.mode !== "skip" && /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [/* @__PURE__ */ (0, J.jsxs)("div", {
												className: "verification-group",
												children: [/* @__PURE__ */ (0, J.jsx)("span", {
													className: "verification-group-label",
													children: n("common.executionSource")
												}), /* @__PURE__ */ (0, J.jsxs)("div", {
													className: "verification-source-toggle",
													children: [/* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
														type: "radio",
														name: `verification-source-${A.name}`,
														checked: P.mode === "auto",
														onChange: () => x(j, { mode: "auto" })
													}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.automaticProfile") }), /* @__PURE__ */ (0, J.jsx)("small", { children: n("common.automaticProfileHelp") })] })] }), /* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
														type: "radio",
														name: `verification-source-${A.name}`,
														checked: P.mode === "custom",
														onChange: () => x(j, { mode: "custom" })
													}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.customCommands") }), /* @__PURE__ */ (0, J.jsx)("small", { children: n("common.customCommandsHelp") })] })] })]
												})]
											}), P.mode === "auto" ? /* @__PURE__ */ (0, J.jsxs)("div", {
												className: "verification-group",
												children: [/* @__PURE__ */ (0, J.jsx)("span", {
													className: "verification-group-label",
													children: n("common.checksToRun")
												}), /* @__PURE__ */ (0, J.jsxs)("div", {
													className: "verification-check-grid",
													children: [/* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
														type: "checkbox",
														checked: P.compile,
														onChange: (e) => x(j, { compile: e.target.checked })
													}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.compileChecks") }), /* @__PURE__ */ (0, J.jsx)("small", { children: n("common.compileChecksHelp") })] })] }), /* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
														type: "checkbox",
														checked: P.tests,
														onChange: (e) => x(j, { tests: e.target.checked })
													}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.tests") }), /* @__PURE__ */ (0, J.jsx)("small", { children: n("common.testsHelp") })] })] })]
												})]
											}) : /* @__PURE__ */ (0, J.jsxs)("div", {
												className: "verification-group",
												children: [/* @__PURE__ */ (0, J.jsx)("span", {
													className: "verification-group-label",
													children: n("common.commands")
												}), /* @__PURE__ */ (0, J.jsxs)("div", {
													className: "verification-command-editor",
													children: [M.suggested_commands?.length > 0 && /* @__PURE__ */ (0, J.jsx)("button", {
														type: "button",
														className: "text-button verification-suggested-button",
														onClick: () => g(j, { delivery_commands: M.suggested_commands.join("\n") }),
														children: n("common.useSuggestedCommands", {
															count: M.suggested_commands.length,
															suffix: Fg === "en" && M.suggested_commands.length === 1 ? "" : Fg === "en" ? "s" : ""
														})
													}), /* @__PURE__ */ (0, J.jsx)("label", {
														className: "field repository-commands",
														children: /* @__PURE__ */ (0, J.jsx)("textarea", {
															value: A.delivery_commands ?? _(A),
															rows: 4,
															placeholder: n("common.oneCommandPerLine"),
															onChange: (e) => g(j, { delivery_commands: e.target.value })
														})
													})]
												})]
											})] })
										]
									})
								]
							})
						}),
						/* @__PURE__ */ (0, J.jsx)("footer", {
							className: "repository-config-footer",
							children: /* @__PURE__ */ (0, J.jsxs)("div", {
								className: "repository-config-actions",
								children: [/* @__PURE__ */ (0, J.jsx)("button", {
									type: "button",
									className: "button",
									disabled: c,
									onClick: () => d(null),
									children: n("common.close")
								}), /* @__PURE__ */ (0, J.jsxs)("button", {
									type: "button",
									className: `button primary${c ? " is-busy" : ""}`,
									disabled: !o || c,
									onClick: () => void S(),
									children: [c ? /* @__PURE__ */ (0, J.jsx)(ag, {
										size: 15,
										className: "spin"
									}) : /* @__PURE__ */ (0, J.jsx)(ug, { size: 15 }), n(c ? "common.saving" : "common.save")]
								})]
							})
						})
					]
				})
			}),
			f && /* @__PURE__ */ (0, J.jsx)(Sv, {
				onClose: () => p(!1),
				onAdd: (e) => {
					t("/api/repositories/clone", { url: e }, "Repository cloned and registered"), p(!1);
				}
			})
		]
	});
}
function Sv({ onClose: e, onAdd: t }) {
	let { t: n } = Z(), [r, i] = (0, I.useState)("");
	return /* @__PURE__ */ (0, J.jsx)("div", {
		className: "modal-backdrop",
		role: "presentation",
		onMouseDown: e,
		children: /* @__PURE__ */ (0, J.jsxs)("section", {
			className: "modal repository-modal",
			role: "dialog",
			"aria-modal": "true",
			"aria-label": n("common.addRepository"),
			onMouseDown: (e) => e.stopPropagation(),
			children: [
				/* @__PURE__ */ (0, J.jsx)("div", {
					className: "prompt-inspector-header",
					children: /* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("strong", { children: n("common.addRepository") }), /* @__PURE__ */ (0, J.jsx)("span", {
						className: "repository-modal-description",
						children: n("common.addRepositoryDescription")
					})] })
				}),
				/* @__PURE__ */ (0, J.jsx)("div", {
					className: "repository-modal-body",
					children: /* @__PURE__ */ (0, J.jsx)($, {
						label: n("common.cloneUrl"),
						children: /* @__PURE__ */ (0, J.jsx)("input", {
							autoFocus: !0,
							value: r,
							placeholder: "https://git.example.com/team/service.git",
							onChange: (e) => i(e.target.value)
						})
					})
				}),
				/* @__PURE__ */ (0, J.jsxs)("footer", { children: [/* @__PURE__ */ (0, J.jsx)("button", {
					className: "button",
					onClick: e,
					children: n("common.cancel")
				}), /* @__PURE__ */ (0, J.jsx)("button", {
					className: "button primary",
					disabled: !r.trim(),
					onClick: () => t(r.trim()),
					children: n("common.cloneInspect")
				})] })
			]
		})
	});
}
function Cv({ data: e, project: t, notify: n, onDirtyChange: r, reload: i }) {
	let { t: a } = Z(), o = e.interactive?.workspace || {}, s = e.interactive?.schedules || {}, c = e.interactive?.agents || {}, [l, u] = (0, I.useState)(String(o.scan_window_days || 7)), [d, f] = (0, I.useState)(String(s.scan?.cron || "0 12 * * 1-5")), [p, m] = (0, I.useState)(!!s.scan), [h, g] = (0, I.useState)(String(Math.round((s.delivery?.interval_seconds || 300) / 60))), [_, v] = (0, I.useState)(Array.isArray(s.delivery?.jira_statuses) ? s.delivery.jira_statuses.map(String) : String(s.delivery?.jira_status || "To Do,Backlog,In Progress").split(",").map((e) => e.trim()).filter(Boolean)), [y, b] = (0, I.useState)(String(s.delivery?.in_dev_status || "")), [x, S] = (0, I.useState)(String(s.delivery?.dev_done_status || "")), [C, w] = (0, I.useState)(String(s.delivery?.blocked_status || "Block")), [T, E] = (0, I.useState)(!!s.delivery?.enabled), [D, O] = (0, I.useState)(String(Math.round((s.patch?.interval_seconds || 300) / 60))), [k, ee] = (0, I.useState)(Array.isArray(s.patch?.jira_statuses) ? s.patch.jira_statuses.map(String) : ["To Do"]), [A, j] = (0, I.useState)(String(s.patch?.in_progress_status || "In Progress")), [M, N] = (0, I.useState)(String(s.patch?.done_status || "Done")), [P, te] = (0, I.useState)(String(s.patch?.blocked_status || "Block")), [ne, re] = (0, I.useState)(!!s.patch?.enabled), [ie, F] = (0, I.useState)(Zg(o.models?.scan)), [ae, oe] = (0, I.useState)(Zg(o.models?.delivery)), [se, ce] = (0, I.useState)(Zg(o.models?.patch)), [le, ue] = (0, I.useState)([]), [de, fe] = (0, I.useState)({}), [pe, me] = (0, I.useState)({}), [he, ge] = (0, I.useState)(String(o.publish?.scan || "pr")), [_e, ve] = (0, I.useState)(String(o.publish?.delivery || "pr")), [ye, be] = (0, I.useState)(String(o.publish?.patch || "pr")), [xe, L] = (0, I.useState)(o.feishu_notifications_enabled !== !1), [Se, Ce] = (0, I.useState)(!!o.deployment_tracking?.enabled), [we, Te] = (0, I.useState)(String(o.deployment_tracking?.provider || "none")), [Ee, De] = (0, I.useState)(String(o.deployment_tracking?.poll_interval_seconds || 30)), [Oe, ke] = (0, I.useState)(String(o.deployment_tracking?.timeout_seconds || 3600)), [Ae, je] = (0, I.useState)(String(o.deployment_tracking?.jenkins?.job || "")), [Me, Ne] = (0, I.useState)(String(o.deployment_tracking?.github_actions?.repository || "")), [Pe, Fe] = (0, I.useState)(String(o.deployment_tracking?.github_actions?.workflow || "")), [Ie, Le] = (0, I.useState)(!!c.enabled), [Re, ze] = (0, I.useState)(Array.isArray(c.agents) ? c.agents.map((e) => ({ ...e })) : []), [Be, Ve] = (0, I.useState)({
		allowed_chat_ids: c.access?.allowed_chat_ids || [],
		allowed_user_ids: c.access?.allowed_user_ids || [],
		mutation_allowed_user_ids: c.access?.mutation_allowed_user_ids || [],
		admin_user_ids: c.access?.admin_user_ids || [],
		legacy_warning: !!c.access?.legacy_warning,
		default_policy: c.access?.default_policy || "legacy_allow"
	}), [He, Ue] = (0, I.useState)({
		user_ids: c.recent_feishu?.user_ids || [],
		chat_ids: c.recent_feishu?.chat_ids || [],
		users: c.recent_feishu?.users || [],
		chats: c.recent_feishu?.chats || [],
		names: c.recent_feishu?.names || {}
	}), [We, Ge] = (0, I.useState)(""), [Ke, qe] = (0, I.useState)(""), [Je, Ye] = (0, I.useState)({
		enabled: !!c.enabled,
		agents: Array.isArray(c.agents) ? JSON.stringify(c.agents) : "[]",
		access: JSON.stringify(c.access || {}),
		testCase: JSON.stringify(c.test_case || {})
	}), [Xe, Ze] = (0, I.useState)({
		language: c.test_case?.language || "zh-Hant",
		table_name: c.test_case?.table_name || "Sheet1",
		base_app_token_env: c.test_case?.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN",
		base_app_token_configured: !!c.test_case?.base_app_token_configured,
		base_app_token_masked: c.test_case?.base_app_token_masked || ""
	}), [Qe, $e] = (0, I.useState)(""), [et, tt] = (0, I.useState)(!1), [nt, rt] = (0, I.useState)(!1), R = () => {
		rt(!0), r(!0);
	}, it = (e) => {
		let t = String(He.names?.[e] || "").trim();
		if (t) return t;
		let n = (He.users || []).find((t) => t.id === e);
		if (n?.name) return String(n.name).trim();
		let r = (He.chats || []).find((t) => t.id === e);
		return String(r?.name || "").trim();
	}, at = (e) => {
		let t = String(e || "").trim();
		return t.length <= 14 ? t : `${t.slice(0, 10)}…${t.slice(-4)}`;
	}, ot = (He.users?.length ? He.users : He.user_ids.map((e) => ({
		id: e,
		name: it(e)
	}))).filter((e) => e.id), st = (He.chats?.length ? He.chats : He.chat_ids.map((e) => ({
		id: e,
		name: it(e)
	}))).filter((e) => e.id), ct = Array.from(/* @__PURE__ */ new Set([
		...Be.allowed_user_ids || [],
		...Be.mutation_allowed_user_ids || [],
		...Be.admin_user_ids || []
	])), lt = /* @__PURE__ */ new Map();
	for (let e of ot) e.id && lt.set(String(e.id), e);
	for (let e of ct) lt.has(e) || lt.set(e, {
		id: e,
		name: it(e)
	});
	let ut = Array.from(lt.values()).filter((e) => e.id), dt = [];
	for (let e of ut) {
		let t = String(e.id), n = String(e.name || it(t) || a("common.unknown")), r = dt.find((e) => e.name === n);
		r ? r.ids.push(t) : dt.push({
			name: n,
			ids: [t]
		});
	}
	let ft = Array.from(/* @__PURE__ */ new Set([...Be.allowed_chat_ids || [], ...He.chat_ids || []])).map((e) => st.find((t) => String(t.id) === e) || {
		id: e,
		name: it(e)
	}), pt = (e, t) => (Be[e] || []).includes(t), mt = (e, t, n) => {
		Ve((r) => {
			let i = r[e] || [];
			return {
				...r,
				[e]: n ? Array.from(/* @__PURE__ */ new Set([...i, t])) : i.filter((e) => e !== t)
			};
		}), R();
	}, ht = dt.filter((e) => e.ids.some((e) => ct.includes(e))), gt = (e) => {
		let t = Array.isArray(e.agents) ? e.agents.map((e) => ({
			...e,
			app_secret: ""
		})) : [], n = {
			allowed_chat_ids: e.access?.allowed_chat_ids || [],
			allowed_user_ids: e.access?.allowed_user_ids || [],
			mutation_allowed_user_ids: e.access?.mutation_allowed_user_ids || [],
			admin_user_ids: e.access?.admin_user_ids || [],
			legacy_warning: !!e.access?.legacy_warning,
			default_policy: e.access?.default_policy || "legacy_allow"
		};
		Le(!!e.enabled), ze(t), Ve(n), Ue({
			user_ids: e.recent_feishu?.user_ids || [],
			chat_ids: e.recent_feishu?.chat_ids || [],
			users: e.recent_feishu?.users || [],
			chats: e.recent_feishu?.chats || [],
			names: e.recent_feishu?.names || {}
		}), Ye({
			enabled: !!e.enabled,
			agents: JSON.stringify(t),
			access: JSON.stringify(n),
			testCase: JSON.stringify(e.test_case || {})
		}), Ze({
			language: e.test_case?.language || "zh-Hant",
			table_name: e.test_case?.table_name || "Sheet1",
			base_app_token_env: e.test_case?.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN",
			base_app_token_configured: !!e.test_case?.base_app_token_configured,
			base_app_token_masked: e.test_case?.base_app_token_masked || ""
		}), $e("");
	}, _t = (e, t) => {
		ze((n) => n.map((n) => n.id === e ? {
			...n,
			...t
		} : n)), R();
	};
	(0, I.useEffect)(() => {
		i_("/api/delivery/status-options", t).then((e) => ue(Array.isArray(e.options) ? e.options.map(String) : [])).catch(() => ue([]));
	}, [t]), (0, I.useEffect)(() => {
		let e = !1;
		return i_("/api/agents", t).then((t) => {
			e || gt(t);
		}).catch(() => void 0), () => {
			e = !0;
		};
	}, [t]), (0, I.useEffect)(() => {
		u(String(o.scan_window_days || 7)), f(String(s.scan?.cron || "0 12 * * 1-5")), m(!!s.scan), g(String(Math.round((s.delivery?.interval_seconds || 300) / 60))), v(Array.isArray(s.delivery?.jira_statuses) ? s.delivery.jira_statuses.map(String) : String(s.delivery?.jira_status || "To Do,Backlog,In Progress").split(",").map((e) => e.trim()).filter(Boolean)), b(String(s.delivery?.in_dev_status || "")), S(String(s.delivery?.dev_done_status || "")), w(String(s.delivery?.blocked_status || "Block")), E(!!s.delivery?.enabled), O(String(Math.round((s.patch?.interval_seconds || 300) / 60))), ee(Array.isArray(s.patch?.jira_statuses) ? s.patch.jira_statuses.map(String) : ["To Do"]), j(String(s.patch?.in_progress_status || "In Progress")), N(String(s.patch?.done_status || "Done")), te(String(s.patch?.blocked_status || "Block")), re(!!s.patch?.enabled), F(Zg(o.models?.scan)), oe(Zg(o.models?.delivery)), ce(Zg(o.models?.patch)), L(o.feishu_notifications_enabled !== !1), fe({}), me({}), e.interactive?.agents && gt(e.interactive.agents), rt(!1), r(!1);
	}, [t]), (0, I.useEffect)(() => {
		ge(String(o.publish?.scan || "pr")), ve(String(o.publish?.delivery || "pr")), be(String(o.publish?.patch || "pr"));
	}, [
		o.publish?.scan,
		o.publish?.delivery,
		o.publish?.patch
	]), (0, I.useEffect)(() => {
		L(o.feishu_notifications_enabled !== !1);
	}, [o.feishu_notifications_enabled]), (0, I.useEffect)(() => {
		let e = o.deployment_tracking || {};
		Ce(!!e.enabled), Te(String(e.provider || "none")), De(String(e.poll_interval_seconds || 30)), ke(String(e.timeout_seconds || 3600)), je(String(e.jenkins?.job || "")), Ne(String(e.github_actions?.repository || "")), Fe(String(e.github_actions?.workflow || ""));
	}, [JSON.stringify(o.deployment_tracking || {})]), (0, I.useEffect)(() => {
		let e = (e) => {
			nt && (e.preventDefault(), e.returnValue = "");
		};
		return window.addEventListener("beforeunload", e), () => window.removeEventListener("beforeunload", e);
	}, [nt]);
	let vt = async (e) => {
		let n = await i_(`/api/integration?key=${encodeURIComponent(e)}`, t);
		return String(n.value);
	}, yt = async (e) => {
		try {
			let t = await vt(e);
			fe((n) => ({
				...n,
				[e]: t
			})), n("Integration value revealed", "success");
		} catch (e) {
			n(e instanceof Error ? e.message : "Unable to reveal value", "error");
		}
	}, bt = async (e) => {
		try {
			let t = await vt(e);
			await navigator.clipboard.writeText(t), n("Integration value copied", "success");
		} catch (e) {
			n(e instanceof Error ? e.message : "Unable to copy value", "error");
		}
	}, xt = o.configured_integrations || [], St = xt.includes("JENKINS_URL") && xt.includes("JENKINS_AUTH"), Ct = Array.from(new Set([
		"To Do",
		"Backlog",
		"In Progress",
		"Done",
		"Block",
		...le,
		..._,
		...k,
		y,
		x,
		A,
		M,
		P
	].filter(Boolean))), wt = Array.isArray(s.delivery?.jira_statuses) ? s.delivery.jira_statuses.map(String) : String(s.delivery?.jira_status || "To Do,Backlog,In Progress").split(",").map((e) => e.trim()).filter(Boolean), Tt = Array.isArray(s.patch?.jira_statuses) ? s.patch.jira_statuses.map(String) : ["To Do"], Et = (e, t) => e.length === t.length && e.every((e, n) => e === t[n]), Dt = p !== !!s.scan || p && d !== String(s.scan?.cron || "0 12 * * 1-5"), Ot = T !== !!s.delivery?.enabled || T && (h !== String(Math.round((s.delivery?.interval_seconds || 300) / 60)) || !Et(_, wt) || y !== String(s.delivery?.in_dev_status || "") || x !== String(s.delivery?.dev_done_status || "") || C !== String(s.delivery?.blocked_status || "Block")), kt = ne !== !!s.patch?.enabled || ne && (D !== String(Math.round((s.patch?.interval_seconds || 300) / 60)) || !Et(k, Tt) || A !== String(s.patch?.in_progress_status || "In Progress") || M !== String(s.patch?.done_status || "Done") || P !== String(s.patch?.blocked_status || "Block")), At = he !== String(o.publish?.scan || "pr") || _e !== String(o.publish?.delivery || "pr") || ye !== String(o.publish?.patch || "pr"), jt = {
		enabled: Se,
		provider: we,
		poll_interval_seconds: Number(Ee),
		timeout_seconds: Number(Oe),
		jenkins: { job: Ae },
		github_actions: {
			repository: Me,
			workflow: Pe
		}
	}, Mt = o.deployment_tracking || {}, Nt = JSON.stringify(jt) !== JSON.stringify({
		enabled: !!Mt.enabled,
		provider: String(Mt.provider || "none"),
		poll_interval_seconds: Number(Mt.poll_interval_seconds || 30),
		timeout_seconds: Number(Mt.timeout_seconds || 3600),
		jenkins: { job: String(Mt.jenkins?.job || "") },
		github_actions: {
			repository: String(Mt.github_actions?.repository || ""),
			workflow: String(Mt.github_actions?.workflow || "")
		}
	}), Pt = Ie !== Je.enabled || JSON.stringify(Re) !== Je.agents || JSON.stringify(Be) !== Je.access || JSON.stringify({
		language: Xe.language || "zh-Hant",
		table_name: Xe.table_name || "Sheet1",
		base_app_token_env: Xe.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN"
	}) !== (() => {
		try {
			let e = JSON.parse(Je.testCase || "{}");
			return JSON.stringify({
				language: e.language || "zh-Hant",
				table_name: e.table_name || "Sheet1",
				base_app_token_env: e.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN"
			});
		} catch {
			return JSON.stringify({
				language: "zh-Hant",
				table_name: "Sheet1",
				base_app_token_env: "FEISHU_MBPASS_QA_SHEET_TOKEN"
			});
		}
	})() || !!Qe.trim(), Ft = async () => {
		if (!et) {
			tt(!0);
			try {
				if (!ie.trim() || !ae.trim() || !se.trim()) throw Error("Choose a preset or enter a Cursor-supported model ID for all workflows.");
				for (let e of Re) if (!String(e.model || "").trim()) throw Error(`${e.display_name || e.id} needs a Cursor model.`);
				let e = [() => i_("/api/workspace", t, {
					method: "POST",
					json: {
						scan_window_days: Number(l),
						scan_model: ie.trim(),
						delivery_model: ae.trim(),
						patch_model: se.trim(),
						feishu_notifications_enabled: xe
					}
				}), ...Object.entries(pe).map(([e, n]) => () => i_("/api/integration", t, {
					method: "POST",
					json: {
						key: e,
						value: n
					}
				}))];
				Dt && e.push(() => i_("/api/schedule", t, {
					method: "POST",
					json: p ? {
						kind: "scan",
						action: "save",
						cron: d
					} : {
						kind: "scan",
						action: "remove"
					}
				})), Ot && e.push(() => i_("/api/schedule", t, {
					method: "POST",
					json: T ? {
						kind: "delivery",
						action: "save",
						interval_minutes: Number(h),
						jira_statuses: _,
						in_dev_status: y,
						dev_done_status: x,
						blocked_status: C
					} : {
						kind: "delivery",
						action: "remove"
					}
				})), kt && e.push(() => i_("/api/schedule", t, {
					method: "POST",
					json: ne ? {
						kind: "patch",
						action: "save",
						interval_minutes: Number(D),
						jira_statuses: k,
						issue_types: ["Task", "Bug"],
						in_progress_status: A,
						done_status: M,
						blocked_status: P
					} : {
						kind: "patch",
						action: "remove"
					}
				})), At && e.push(() => i_("/api/publish-policy", t, {
					method: "POST",
					json: {
						scan_mode: he,
						delivery_mode: _e,
						patch_mode: ye
					}
				})), Nt && e.push(() => i_("/api/deployment-config", t, {
					method: "POST",
					json: jt
				})), Pt && e.push(async () => {
					let e = await i_("/api/agents", t, {
						method: "POST",
						json: {
							enabled: Ie,
							access: Be,
							test_case: {
								destination: "sheet",
								language: Xe.language || "zh-Hant",
								table_name: Xe.table_name || "Sheet1",
								base_app_token_env: Xe.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN",
								...Qe.trim() ? { base_app_token: Qe.trim() } : {}
							},
							agents: Re.map((e) => {
								let t = {
									id: e.id,
									role: e.role,
									workflow: e.workflow,
									conversation_enabled: e.conversation_enabled,
									mode: e.mode,
									model: e.model,
									soft_timeout_seconds: Number(e.soft_timeout_seconds),
									hard_timeout_seconds: Number(e.hard_timeout_seconds),
									reaction_enabled: e.reaction_enabled,
									max_concurrent_jobs: Number(e.max_concurrent_jobs),
									soul_version: e.soul_version,
									soul: e.soul,
									app_id: String(e.app_id || "").trim()
								}, n = String(e.app_secret || "").trim();
								return n && (t.app_secret = n), t;
							})
						}
					});
					gt(e);
				});
				for (let t of e) await t();
				me({}), rt(!1), r(!1), n("Settings saved", "success"), i();
			} catch (e) {
				n(e instanceof Error ? e.message : "Unable to save Settings", "error");
			} finally {
				tt(!1);
			}
		}
	}, It = [
		p,
		T,
		ne
	].filter(Boolean).length, Lt = Re.filter((e) => e.conversation_enabled).length;
	return /* @__PURE__ */ (0, J.jsxs)("div", {
		className: "settings-stack",
		children: [
			/* @__PURE__ */ (0, J.jsx)(M_, {
				title: a("heading.workspaceSettings"),
				description: `${t || a("common.currentProject")} · ${a("context.settings.description")}`,
				action: /* @__PURE__ */ (0, J.jsx)("span", {
					className: "settings-scope",
					children: a("settings.localConfiguration")
				})
			}),
			/* @__PURE__ */ (0, J.jsxs)("div", {
				className: "settings-summary",
				children: [
					/* @__PURE__ */ (0, J.jsxs)("div", { children: [
						/* @__PURE__ */ (0, J.jsx)("span", { children: a("common.schedules") }),
						/* @__PURE__ */ (0, J.jsxs)("strong", { children: [It, "/3"] }),
						/* @__PURE__ */ (0, J.jsx)("small", { children: a("common.active") })
					] }),
					/* @__PURE__ */ (0, J.jsxs)("div", { children: [
						/* @__PURE__ */ (0, J.jsx)("span", { children: a("common.agentConversations") }),
						/* @__PURE__ */ (0, J.jsxs)("strong", { children: [
							Lt,
							"/",
							Re.length || 4
						] }),
						/* @__PURE__ */ (0, J.jsx)("small", { children: a("common.enabled") })
					] }),
					/* @__PURE__ */ (0, J.jsxs)("div", { children: [
						/* @__PURE__ */ (0, J.jsx)("span", { children: a("heading.publishPolicy") }),
						/* @__PURE__ */ (0, J.jsx)("strong", { children: a(_e === "direct" ? "settings.direct" : _e === "merge" ? "settings.merge" : "settings.pullRequest") }),
						/* @__PURE__ */ (0, J.jsx)("small", { children: a("label.autoDelivery") })
					] }),
					/* @__PURE__ */ (0, J.jsxs)("div", { children: [
						/* @__PURE__ */ (0, J.jsx)("span", { children: a("common.integrations") }),
						/* @__PURE__ */ (0, J.jsx)("strong", { children: xt.length }),
						/* @__PURE__ */ (0, J.jsx)("small", { children: a("common.configuredKeys") })
					] })
				]
			}),
			/* @__PURE__ */ (0, J.jsxs)("nav", {
				className: "settings-nav",
				"aria-label": a("common.settingsSections"),
				children: [
					/* @__PURE__ */ (0, J.jsx)("a", {
						href: "#settings-automation",
						children: a("settings.automation")
					}),
					/* @__PURE__ */ (0, J.jsx)("a", {
						href: "#settings-agents",
						children: a("settings.agentTeam")
					}),
					/* @__PURE__ */ (0, J.jsx)("a", {
						href: "#settings-project",
						children: a("settings.projectOutput")
					}),
					/* @__PURE__ */ (0, J.jsx)("a", {
						href: "#settings-runtime",
						children: a("settings.runtime")
					})
				]
			}),
			/* @__PURE__ */ (0, J.jsxs)("section", {
				className: "settings-cluster",
				id: "settings-automation",
				children: [/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "settings-cluster-heading",
					children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [
						/* @__PURE__ */ (0, J.jsx)("span", { children: a("settings.controlPlane") }),
						/* @__PURE__ */ (0, J.jsx)("h2", { children: a("settings.automation") }),
						/* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.automationDescription") })
					] }), /* @__PURE__ */ (0, J.jsxs)("a", {
						href: "#settings-agents",
						children: [
							a("settings.nextAgentTeam"),
							" ",
							/* @__PURE__ */ (0, J.jsx)(Bh, { size: 13 })
						]
					})]
				}), /* @__PURE__ */ (0, J.jsxs)(k_, {
					title: a("heading.automationSchedules"),
					children: [
						/* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section",
							children: [
								/* @__PURE__ */ (0, J.jsxs)("div", {
									className: "settings-copy",
									children: [/* @__PURE__ */ (0, J.jsx)("div", {
										className: "settings-heading",
										children: /* @__PURE__ */ (0, J.jsx)("div", {
											className: "settings-title-stack",
											children: /* @__PURE__ */ (0, J.jsx)("h4", { children: a("label.autoScan") })
										})
									}), /* @__PURE__ */ (0, J.jsx)("p", { children: Q(s.scan?.description, a("settings.scanDefaultDescription")) })]
								}),
								/* @__PURE__ */ (0, J.jsx)("div", {
									className: "settings-control wide",
									children: /* @__PURE__ */ (0, J.jsxs)("div", {
										className: "form-grid compact scan-settings-fields",
										style: {
											display: "grid",
											gridTemplateColumns: "1fr 1fr",
											gap: 12,
											padding: 0,
											width: "100%"
										},
										children: [/* @__PURE__ */ (0, J.jsx)($, {
											label: a("label.lookbackDays"),
											children: /* @__PURE__ */ (0, J.jsx)("input", {
												type: "number",
												min: "1",
												max: "365",
												value: l,
												onChange: (e) => {
													u(e.target.value), R();
												}
											})
										}), /* @__PURE__ */ (0, J.jsx)($, {
											label: a("label.cron"),
											children: /* @__PURE__ */ (0, J.jsx)("input", {
												value: d,
												onChange: (e) => {
													f(e.target.value), R();
												}
											})
										})]
									})
								}),
								/* @__PURE__ */ (0, J.jsx)("div", {
									className: "settings-toggle",
									children: /* @__PURE__ */ (0, J.jsx)(wv, {
										enabled: p,
										onChange: (e) => {
											m(e), R();
										}
									})
								})
							]
						}),
						/* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section divider",
							children: [
								/* @__PURE__ */ (0, J.jsxs)("div", {
									className: "settings-copy",
									children: [/* @__PURE__ */ (0, J.jsx)("div", {
										className: "settings-heading",
										children: /* @__PURE__ */ (0, J.jsx)("div", {
											className: "settings-title-stack",
											children: /* @__PURE__ */ (0, J.jsx)("h4", { children: a("label.autoDelivery") })
										})
									}), /* @__PURE__ */ (0, J.jsx)("p", { children: T ? `Polling every ${h} minute(s).` : a("settings.deliveryPaused") })]
								}),
								/* @__PURE__ */ (0, J.jsxs)("div", {
									className: "settings-control wide",
									children: [/* @__PURE__ */ (0, J.jsxs)("div", {
										className: "form-grid compact",
										children: [
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.intervalMinutes"),
												children: /* @__PURE__ */ (0, J.jsx)("input", {
													type: "number",
													min: "1",
													value: h,
													onChange: (e) => {
														g(e.target.value), R();
													}
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.eligibleStatuses"),
												help: a("settings.deliveryStatusHelp"),
												children: /* @__PURE__ */ (0, J.jsx)(vv, {
													options: Ct,
													value: _,
													onChange: v,
													markDirty: R
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.moveStarted"),
												children: /* @__PURE__ */ (0, J.jsx)("select", {
													value: y,
													onChange: (e) => {
														b(e.target.value), R();
													},
													children: Ct.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
														value: e,
														children: e
													}, e))
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.moveCompleted"),
												children: /* @__PURE__ */ (0, J.jsx)("select", {
													value: x,
													onChange: (e) => {
														S(e.target.value), R();
													},
													children: Ct.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
														value: e,
														children: e
													}, e))
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.moveFailed"),
												children: /* @__PURE__ */ (0, J.jsx)("select", {
													value: C,
													onChange: (e) => {
														w(e.target.value), R();
													},
													children: Array.from(/* @__PURE__ */ new Set([...Ct, "Block"])).map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
														value: e,
														children: e
													}, e))
												})
											})
										]
									}), /* @__PURE__ */ (0, J.jsx)("p", {
										className: "schedule-note",
										children: a("settings.deliveryStatusNote")
									})]
								}),
								/* @__PURE__ */ (0, J.jsx)("div", {
									className: "settings-toggle",
									children: /* @__PURE__ */ (0, J.jsx)(wv, {
										enabled: T,
										onChange: (e) => {
											E(e), R();
										}
									})
								})
							]
						}),
						/* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section divider",
							children: [
								/* @__PURE__ */ (0, J.jsxs)("div", {
									className: "settings-copy",
									children: [/* @__PURE__ */ (0, J.jsx)("div", {
										className: "settings-heading",
										children: /* @__PURE__ */ (0, J.jsx)("div", {
											className: "settings-title-stack",
											children: /* @__PURE__ */ (0, J.jsx)("h4", { children: a("label.autoPatch") })
										})
									}), /* @__PURE__ */ (0, J.jsx)("p", { children: ne ? `Polling every ${D} minute(s) for Task and Bug cards.` : a("settings.patchPaused") })]
								}),
								/* @__PURE__ */ (0, J.jsxs)("div", {
									className: "settings-control wide",
									children: [/* @__PURE__ */ (0, J.jsxs)("div", {
										className: "form-grid compact",
										children: [
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.intervalMinutes"),
												children: /* @__PURE__ */ (0, J.jsx)("input", {
													type: "number",
													min: "1",
													value: D,
													onChange: (e) => {
														O(e.target.value), R();
													}
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.eligibleStatuses"),
												children: /* @__PURE__ */ (0, J.jsx)(vv, {
													options: Ct,
													value: k,
													onChange: ee,
													markDirty: R
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.moveStarted"),
												children: /* @__PURE__ */ (0, J.jsx)("select", {
													value: A,
													onChange: (e) => {
														j(e.target.value), R();
													},
													children: Ct.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
														value: e,
														children: e
													}, e))
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.moveCompleted"),
												children: /* @__PURE__ */ (0, J.jsx)("select", {
													value: M,
													onChange: (e) => {
														N(e.target.value), R();
													},
													children: Ct.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
														value: e,
														children: e
													}, e))
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.moveBlocked"),
												children: /* @__PURE__ */ (0, J.jsx)("select", {
													value: P,
													onChange: (e) => {
														te(e.target.value), R();
													},
													children: Ct.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
														value: e,
														children: e
													}, e))
												})
											})
										]
									}), /* @__PURE__ */ (0, J.jsx)("p", {
										className: "schedule-note",
										children: a("settings.patchStatusNote")
									})]
								}),
								/* @__PURE__ */ (0, J.jsx)("div", {
									className: "settings-toggle",
									children: /* @__PURE__ */ (0, J.jsx)(wv, {
										enabled: ne,
										onChange: (e) => {
											re(e), R();
										}
									})
								})
							]
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, J.jsxs)("section", {
				className: "settings-cluster",
				id: "settings-agents",
				children: [/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "settings-cluster-heading",
					children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [
						/* @__PURE__ */ (0, J.jsx)("span", { children: a("settings.humanAgents") }),
						/* @__PURE__ */ (0, J.jsx)("h2", { children: a("settings.agentTeam") }),
						/* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.agentTeamDescription") })
					] }), /* @__PURE__ */ (0, J.jsxs)("a", {
						href: "#settings-project",
						children: [
							a("settings.nextProjectOutput"),
							" ",
							/* @__PURE__ */ (0, J.jsx)(Bh, { size: 13 })
						]
					})]
				}), /* @__PURE__ */ (0, J.jsxs)(k_, {
					title: a("heading.agentRoles"),
					action: /* @__PURE__ */ (0, J.jsx)("span", {
						className: "muted",
						children: a("settings.globalFeishuAgents")
					}),
					children: [
						/* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section",
							children: [/* @__PURE__ */ (0, J.jsxs)("div", {
								className: "settings-copy",
								children: [/* @__PURE__ */ (0, J.jsx)("div", {
									className: "settings-heading",
									children: /* @__PURE__ */ (0, J.jsx)("div", {
										className: "settings-title-stack",
										children: /* @__PURE__ */ (0, J.jsx)("h4", { children: a("label.gateway") })
									})
								}), /* @__PURE__ */ (0, J.jsxs)("p", { children: [
									"Enable Feishu conversational agents. Config lives in ",
									Q(c.config_path, "~/.lumon/agents/config.json"),
									". Restart `lumon agents start` after saving. Mutations fail closed until mutation users are configured."
								] })]
							}), /* @__PURE__ */ (0, J.jsx)("div", {
								className: "settings-toggle",
								children: /* @__PURE__ */ (0, J.jsx)(wv, {
									enabled: Ie,
									onChange: (e) => {
										Le(e), R();
									}
								})
							})]
						}),
						/* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section divider access-control-section",
							children: [/* @__PURE__ */ (0, J.jsxs)("div", {
								className: "settings-copy",
								children: [
									/* @__PURE__ */ (0, J.jsx)("div", {
										className: "settings-heading",
										children: /* @__PURE__ */ (0, J.jsx)("div", {
											className: "settings-title-stack",
											children: /* @__PURE__ */ (0, J.jsx)("h4", { children: a("settings.accessControl") })
										})
									}),
									/* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.accessControlDescription") }),
									!!(Be.legacy_warning ?? c.access?.legacy_warning) && /* @__PURE__ */ (0, J.jsx)("p", {
										className: "schedule-note",
										children: a("settings.legacyWarning")
									})
								]
							}), /* @__PURE__ */ (0, J.jsxs)("div", {
								className: "settings-control wide access-control-panel",
								children: [
									/* @__PURE__ */ (0, J.jsxs)("div", {
										className: "access-selector-grid",
										children: [/* @__PURE__ */ (0, J.jsx)($, {
											label: a("settings.accessPerson"),
											help: a("settings.selectIdentityHelp"),
											children: /* @__PURE__ */ (0, J.jsxs)("select", {
												value: We,
												onChange: (e) => Ge(e.target.value),
												children: [/* @__PURE__ */ (0, J.jsx)("option", {
													value: "",
													children: a("settings.selectPerson")
												}), dt.map((e) => /* @__PURE__ */ (0, J.jsx)("optgroup", {
													label: `${e.name} · ${e.ids.length}`,
													children: e.ids.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
														value: e,
														children: at(e)
													}, e))
												}, e.name))]
											})
										}), /* @__PURE__ */ (0, J.jsx)($, {
											label: a("settings.accessChat"),
											help: a("settings.allowedChatHelp"),
											children: /* @__PURE__ */ (0, J.jsxs)("select", {
												value: Ke,
												onChange: (e) => qe(e.target.value),
												children: [/* @__PURE__ */ (0, J.jsx)("option", {
													value: "",
													children: a("settings.selectChat")
												}), ft.map((e) => /* @__PURE__ */ (0, J.jsx)("option", {
													value: String(e.id),
													children: e.name || it(String(e.id)) || at(String(e.id))
												}, String(e.id)))]
											})
										})]
									}),
									We && /* @__PURE__ */ (0, J.jsxs)("div", {
										className: "access-identity-editor",
										children: [
											/* @__PURE__ */ (0, J.jsxs)("div", {
												className: "access-identity-heading",
												children: [/* @__PURE__ */ (0, J.jsx)("span", { children: a("settings.identityRoles") }), /* @__PURE__ */ (0, J.jsx)("code", { children: at(We) })]
											}),
											/* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
												type: "checkbox",
												checked: pt("allowed_user_ids", We),
												onChange: (e) => mt("allowed_user_ids", We, e.target.checked)
											}), a("settings.canTalk")] }),
											/* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
												type: "checkbox",
												checked: pt("mutation_allowed_user_ids", We),
												onChange: (e) => mt("mutation_allowed_user_ids", We, e.target.checked)
											}), a("settings.canMutate")] }),
											/* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
												type: "checkbox",
												checked: pt("admin_user_ids", We),
												onChange: (e) => mt("admin_user_ids", We, e.target.checked)
											}), a("settings.canAdmin")] })
										]
									}),
									Ke && /* @__PURE__ */ (0, J.jsxs)("div", {
										className: "access-identity-editor",
										children: [/* @__PURE__ */ (0, J.jsxs)("div", {
											className: "access-identity-heading",
											children: [/* @__PURE__ */ (0, J.jsx)("span", { children: a("settings.accessChat") }), /* @__PURE__ */ (0, J.jsx)("code", { children: at(Ke) })]
										}), /* @__PURE__ */ (0, J.jsxs)("label", { children: [/* @__PURE__ */ (0, J.jsx)("input", {
											type: "checkbox",
											checked: (Be.allowed_chat_ids || []).includes(Ke),
											onChange: (e) => mt("allowed_chat_ids", Ke, e.target.checked)
										}), a("settings.allowChat")] })]
									}),
									ht.length > 0 && /* @__PURE__ */ (0, J.jsxs)("div", {
										className: "access-summary",
										children: [/* @__PURE__ */ (0, J.jsxs)("div", {
											className: "access-identity-heading",
											children: [/* @__PURE__ */ (0, J.jsx)("span", { children: a("settings.accessSummary") }), /* @__PURE__ */ (0, J.jsx)("small", { children: a("settings.identityCount", { count: ht.reduce((e, t) => e + t.ids.length, 0) }) })]
										}), ht.map((e) => /* @__PURE__ */ (0, J.jsxs)("button", {
											type: "button",
											className: "access-summary-row",
											onClick: () => Ge(e.ids[0]),
											children: [
												/* @__PURE__ */ (0, J.jsx)("strong", { children: e.name }),
												/* @__PURE__ */ (0, J.jsx)("span", { children: a("settings.identityCount", { count: e.ids.length }) }),
												/* @__PURE__ */ (0, J.jsxs)("em", { children: [
													[
														"allowed_user_ids",
														"mutation_allowed_user_ids",
														"admin_user_ids"
													].filter((t) => e.ids.some((e) => pt(t, e))).length,
													" ",
													a("settings.rolesApplied")
												] })
											]
										}, e.name))]
									}),
									ut.length === 0 && /* @__PURE__ */ (0, J.jsx)("p", {
										className: "schedule-note access-empty-note",
										children: a("settings.noRecentPeople")
									})
								]
							})]
						}),
						Re.map((e) => {
							let t = Jg(Wg(e.workflow) || Ug, a);
							return /* @__PURE__ */ (0, J.jsxs)("div", {
								className: "settings-section divider agent-role-section",
								children: [/* @__PURE__ */ (0, J.jsxs)("div", {
									className: "settings-copy",
									children: [
										/* @__PURE__ */ (0, J.jsxs)("div", {
											className: "settings-heading",
											children: [/* @__PURE__ */ (0, J.jsx)("div", {
												className: "settings-title-stack",
												children: /* @__PURE__ */ (0, J.jsxs)("div", {
													className: "agent-settings-identity",
													children: [/* @__PURE__ */ (0, J.jsx)(qg, {
														agentId: e.id,
														displayName: e.display_name,
														size: "guide"
													}), /* @__PURE__ */ (0, J.jsxs)("span", { children: [/* @__PURE__ */ (0, J.jsx)("h4", { children: e.display_name }), /* @__PURE__ */ (0, J.jsx)("small", { children: e.title })] })]
												})
											}), /* @__PURE__ */ (0, J.jsx)(a_, { value: e.conversation_enabled ? a("common.enabled") : a("common.paused") })]
										}),
										/* @__PURE__ */ (0, J.jsx)("p", { children: t.mission }),
										/* @__PURE__ */ (0, J.jsxs)("div", {
											className: "agent-settings-responsibility",
											children: [
												/* @__PURE__ */ (0, J.jsx)("span", { children: a("settings.responsibility") }),
												/* @__PURE__ */ (0, J.jsx)("strong", { children: t.feature }),
												/* @__PURE__ */ (0, J.jsx)("span", { children: a("label.role") }),
												/* @__PURE__ */ (0, J.jsx)("strong", { children: e.role }),
												/* @__PURE__ */ (0, J.jsx)("span", { children: a("label.workflow") }),
												/* @__PURE__ */ (0, J.jsx)("strong", { children: e.workflow })
											]
										}),
										/* @__PURE__ */ (0, J.jsxs)("p", {
											className: "schedule-note",
											children: [
												a("settings.agentCoreDescription"),
												" Credentials live in ",
												Q(e.credentials_path, "~/.lumon/.env.local"),
												"."
											]
										})
									]
								}), /* @__PURE__ */ (0, J.jsx)("div", {
									className: "settings-control wide",
									children: /* @__PURE__ */ (0, J.jsxs)("div", {
										className: "form-grid compact agent-core-fields",
										children: [
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.feishuAppId"),
												children: /* @__PURE__ */ (0, J.jsx)("input", {
													value: e.app_id || "",
													placeholder: e.app_id_masked || "cli_…",
													onChange: (t) => _t(e.id, { app_id: t.target.value })
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.feishuAppSecret"),
												help: e.app_secret_configured ? `Configured (${e.app_secret_masked || "set"}). Leave blank to keep.` : a("settings.appSecretRequired"),
												children: /* @__PURE__ */ (0, J.jsx)("input", {
													type: "password",
													value: e.app_secret || "",
													placeholder: e.app_secret_configured ? a("settings.keepSecret") : a("settings.enterSecret"),
													onChange: (t) => _t(e.id, { app_secret: t.target.value }),
													autoComplete: "new-password"
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("label.conversation"),
												children: /* @__PURE__ */ (0, J.jsxs)("select", {
													value: e.conversation_enabled ? "on" : "off",
													onChange: (t) => _t(e.id, { conversation_enabled: t.target.value === "on" }),
													children: [/* @__PURE__ */ (0, J.jsx)("option", {
														value: "on",
														children: a("common.enabled")
													}), /* @__PURE__ */ (0, J.jsx)("option", {
														value: "off",
														children: a("common.paused")
													})]
												})
											}),
											/* @__PURE__ */ (0, J.jsx)(yv, {
												label: a("label.cursorModel"),
												value: e.model,
												onChange: (t) => _t(e.id, { model: t }),
												markDirty: R
											})
										]
									})
								})]
							}, e.id);
						}),
						Re.length === 0 && /* @__PURE__ */ (0, J.jsx)("div", {
							className: "settings-section divider",
							children: /* @__PURE__ */ (0, J.jsx)(W_, { label: a("common.noAgentRolesSettings") })
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, J.jsxs)("section", {
				className: "settings-cluster",
				id: "settings-project",
				children: [/* @__PURE__ */ (0, J.jsxs)("div", {
					className: "settings-cluster-heading",
					children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [
						/* @__PURE__ */ (0, J.jsx)("span", { children: a("settings.businessOutput") }),
						/* @__PURE__ */ (0, J.jsx)("h2", { children: a("settings.projectOutput") }),
						/* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.projectOutputDescription") })
					] }), /* @__PURE__ */ (0, J.jsxs)("a", {
						href: "#settings-runtime",
						children: [
							a("settings.nextRuntime"),
							" ",
							/* @__PURE__ */ (0, J.jsx)(Bh, { size: 13 })
						]
					})]
				}), /* @__PURE__ */ (0, J.jsx)(k_, {
					title: a("heading.testCases"),
					action: /* @__PURE__ */ (0, J.jsxs)("span", {
						className: "muted",
						children: ["Mark · ", t || a("common.project")]
					}),
					children: /* @__PURE__ */ (0, J.jsxs)("div", {
						className: "settings-section",
						children: [/* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-copy",
							children: [/* @__PURE__ */ (0, J.jsx)("div", {
								className: "settings-heading",
								children: /* @__PURE__ */ (0, J.jsx)("div", {
									className: "settings-title-stack",
									children: /* @__PURE__ */ (0, J.jsx)("h4", { children: a("settings.generationLanguage") })
								})
							}), /* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.generationDescription") })]
						}), /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-control wide",
							children: [/* @__PURE__ */ (0, J.jsxs)("div", {
								className: "form-grid compact",
								children: [
									/* @__PURE__ */ (0, J.jsx)($, {
										label: a("label.outputLanguage"),
										children: /* @__PURE__ */ (0, J.jsxs)("select", {
											value: Xe.language || "zh-Hant",
											onChange: (e) => {
												Ze((t) => ({
													...t,
													language: e.target.value
												})), R();
											},
											children: [
												/* @__PURE__ */ (0, J.jsxs)("option", {
													value: "zh-Hant",
													children: [a("language.zhHant"), " (zh-Hant)"]
												}),
												/* @__PURE__ */ (0, J.jsxs)("option", {
													value: "zh-Hans",
													children: [a("language.zhHans"), " (zh-Hans)"]
												}),
												/* @__PURE__ */ (0, J.jsx)("option", {
													value: "en",
													children: a("language.en")
												})
											]
										})
									}),
									/* @__PURE__ */ (0, J.jsx)($, {
										label: a("label.spreadsheetTab"),
										children: /* @__PURE__ */ (0, J.jsx)("input", {
											value: Xe.table_name || "Sheet1",
											onChange: (e) => {
												Ze((t) => ({
													...t,
													table_name: e.target.value
												})), R();
											}
										})
									}),
									/* @__PURE__ */ (0, J.jsx)($, {
										label: a("label.spreadsheetToken"),
										help: Xe.base_app_token_configured ? `Configured (${Xe.base_app_token_masked || "set"}). Leave blank to keep. Env: ${Xe.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN"}` : `Stored in ~/.lumon/.env.local as ${Xe.base_app_token_env || "FEISHU_MBPASS_QA_SHEET_TOKEN"}`,
										children: /* @__PURE__ */ (0, J.jsx)("input", {
											value: Qe,
											placeholder: Xe.base_app_token_configured ? "Leave blank to keep current token" : "https://…/sheets/TOKEN or TOKEN",
											onChange: (e) => {
												$e(e.target.value), R();
											},
											autoComplete: "off"
										})
									})
								]
							}), /* @__PURE__ */ (0, J.jsx)("p", {
								className: "schedule-note",
								children: a("settings.afterGeneration")
							})]
						})]
					})
				})]
			}),
			/* @__PURE__ */ (0, J.jsxs)("section", {
				className: "settings-cluster",
				id: "settings-runtime",
				children: [
					/* @__PURE__ */ (0, J.jsxs)("div", {
						className: "settings-cluster-heading",
						children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [
							/* @__PURE__ */ (0, J.jsx)("span", { children: a("settings.operatingDetails") }),
							/* @__PURE__ */ (0, J.jsx)("h2", { children: a("settings.runtime") }),
							/* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.runtimeDescription") })
						] }), /* @__PURE__ */ (0, J.jsxs)("a", {
							href: "#settings-automation",
							children: [
								a("settings.backAutomation"),
								" ",
								/* @__PURE__ */ (0, J.jsx)(Rh, { size: 13 })
							]
						})]
					}),
					/* @__PURE__ */ (0, J.jsx)(k_, {
						title: a("heading.executionModels"),
						children: /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section",
							children: [/* @__PURE__ */ (0, J.jsxs)("div", {
								className: "settings-copy",
								children: [/* @__PURE__ */ (0, J.jsx)("h4", { children: a("label.cursorModel") }), /* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.executionDescription") })]
							}), /* @__PURE__ */ (0, J.jsx)("div", {
								className: "settings-control wide",
								children: /* @__PURE__ */ (0, J.jsxs)("div", {
									className: "form-grid compact",
									children: [
										/* @__PURE__ */ (0, J.jsx)(yv, {
											label: `${a("label.autoScan")} model`,
											value: ie,
											onChange: F,
											markDirty: R
										}),
										/* @__PURE__ */ (0, J.jsx)(yv, {
											label: `${a("label.autoDelivery")} model`,
											value: ae,
											onChange: oe,
											markDirty: R
										}),
										/* @__PURE__ */ (0, J.jsx)(yv, {
											label: `${a("label.autoPatch")} model`,
											value: se,
											onChange: ce,
											markDirty: R
										})
									]
								})
							})]
						})
					}),
					/* @__PURE__ */ (0, J.jsx)(k_, {
						title: a("heading.publishPolicy"),
						children: /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section",
							children: [/* @__PURE__ */ (0, J.jsxs)("div", {
								className: "settings-copy",
								children: [/* @__PURE__ */ (0, J.jsx)("h4", { children: a("settings.automationOutcome") }), /* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.publishDescription") })]
							}), /* @__PURE__ */ (0, J.jsx)("div", {
								className: "settings-control wide",
								children: /* @__PURE__ */ (0, J.jsxs)("div", {
									className: "form-grid compact",
									children: [
										/* @__PURE__ */ (0, J.jsx)($, {
											label: a("label.autoScan"),
											children: /* @__PURE__ */ (0, J.jsxs)("select", {
												value: he,
												onChange: (e) => {
													ge(e.target.value), R();
												},
												children: [/* @__PURE__ */ (0, J.jsx)("option", {
													value: "pr",
													children: a("settings.openPullRequest")
												}), /* @__PURE__ */ (0, J.jsx)("option", {
													value: "merge",
													children: a("settings.mergeAfterPullRequest")
												})]
											})
										}),
										/* @__PURE__ */ (0, J.jsx)($, {
											label: a("label.autoDelivery"),
											children: /* @__PURE__ */ (0, J.jsxs)("select", {
												value: _e,
												onChange: (e) => {
													ve(e.target.value), R();
												},
												children: [
													/* @__PURE__ */ (0, J.jsx)("option", {
														value: "pr",
														children: a("settings.openPullRequest")
													}),
													/* @__PURE__ */ (0, J.jsx)("option", {
														value: "merge",
														children: a("settings.mergeAfterPullRequest")
													}),
													/* @__PURE__ */ (0, J.jsx)("option", {
														value: "direct",
														children: a("settings.pushDirectly")
													})
												]
											})
										}),
										/* @__PURE__ */ (0, J.jsx)($, {
											label: a("label.autoPatch"),
											children: /* @__PURE__ */ (0, J.jsxs)("select", {
												value: ye,
												onChange: (e) => {
													be(e.target.value), R();
												},
												children: [/* @__PURE__ */ (0, J.jsx)("option", {
													value: "pr",
													children: a("settings.openPullRequest")
												}), /* @__PURE__ */ (0, J.jsx)("option", {
													value: "direct",
													children: a("settings.pushDirectly")
												})]
											})
										})
									]
								})
							})]
						})
					}),
					/* @__PURE__ */ (0, J.jsx)(k_, {
						title: a("settings.deploymentTracking"),
						children: /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section",
							children: [
								/* @__PURE__ */ (0, J.jsxs)("div", {
									className: "settings-copy deployment-tracking-copy",
									children: [
										/* @__PURE__ */ (0, J.jsx)("h4", { children: a("settings.deploymentTracking") }),
										/* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.deploymentTrackingDescription") }),
										/* @__PURE__ */ (0, J.jsxs)("div", {
											className: "deployment-policy-note",
											children: [
												/* @__PURE__ */ (0, J.jsx)("span", {
													className: "field-label",
													children: a("settings.deploymentOwner")
												}),
												/* @__PURE__ */ (0, J.jsx)("strong", { children: a("settings.deploymentOwnerValue") }),
												/* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.deploymentFailureHandling") })
											]
										})
									]
								}),
								/* @__PURE__ */ (0, J.jsx)("div", {
									className: "settings-control wide deployment-settings-control",
									children: /* @__PURE__ */ (0, J.jsxs)("div", {
										className: "form-grid compact",
										children: [
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("settings.deploymentProvider"),
												help: a("settings.deploymentProviderHelp"),
												children: /* @__PURE__ */ (0, J.jsxs)("select", {
													value: we,
													onChange: (e) => {
														Te(e.target.value), Ce(e.target.value !== "none"), R();
													},
													children: [
														/* @__PURE__ */ (0, J.jsx)("option", {
															value: "none",
															children: a("settings.deploymentDisabled")
														}),
														/* @__PURE__ */ (0, J.jsx)("option", {
															value: "jenkins",
															children: a("settings.jenkins")
														}),
														/* @__PURE__ */ (0, J.jsx)("option", {
															value: "github_actions",
															children: a("settings.githubActions")
														})
													]
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("settings.deploymentOwner"),
												help: a("settings.deploymentOwnerHelp"),
												children: /* @__PURE__ */ (0, J.jsx)("div", {
													className: "settings-static-value",
													children: a("settings.deploymentOwnerValue")
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("settings.pollInterval"),
												children: /* @__PURE__ */ (0, J.jsx)("input", {
													type: "number",
													min: "5",
													value: Ee,
													onChange: (e) => {
														De(e.target.value), R();
													}
												})
											}),
											/* @__PURE__ */ (0, J.jsx)($, {
												label: a("settings.deploymentTimeout"),
												children: /* @__PURE__ */ (0, J.jsx)("input", {
													type: "number",
													min: "60",
													value: Oe,
													onChange: (e) => {
														ke(e.target.value), R();
													}
												})
											}),
											we === "jenkins" && /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [/* @__PURE__ */ (0, J.jsx)($, {
												label: a("settings.jenkinsPipeline"),
												help: a("settings.jenkinsPipelineHelp"),
												children: /* @__PURE__ */ (0, J.jsx)("input", {
													value: Ae,
													placeholder: "folder/job-name",
													onChange: (e) => {
														je(e.target.value), R();
													}
												})
											}), /* @__PURE__ */ (0, J.jsxs)("div", {
												className: "deployment-credentials",
												children: [
													/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("span", {
														className: "field-label",
														children: a("settings.credentials")
													}), /* @__PURE__ */ (0, J.jsx)("span", {
														className: `integration-status${St ? " is-configured" : ""}`,
														children: a(St ? "settings.configured" : "settings.notConfigured")
													})] }),
													/* @__PURE__ */ (0, J.jsx)("code", { children: "JENKINS_URL + JENKINS_AUTH" }),
													/* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.jenkinsCredentials") })
												]
											})] }),
											we === "github_actions" && /* @__PURE__ */ (0, J.jsxs)(J.Fragment, { children: [
												/* @__PURE__ */ (0, J.jsx)($, {
													label: a("settings.githubRepository"),
													children: /* @__PURE__ */ (0, J.jsx)("input", {
														value: Me,
														placeholder: "owner/repository",
														onChange: (e) => {
															Ne(e.target.value), R();
														}
													})
												}),
												/* @__PURE__ */ (0, J.jsx)($, {
													label: a("settings.githubWorkflow"),
													children: /* @__PURE__ */ (0, J.jsx)("input", {
														value: Pe,
														placeholder: "deploy.yml",
														onChange: (e) => {
															Fe(e.target.value), R();
														}
													})
												}),
												/* @__PURE__ */ (0, J.jsxs)("div", {
													className: "deployment-credentials",
													children: [/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)("span", {
														className: "field-label",
														children: a("settings.credentials")
													}), /* @__PURE__ */ (0, J.jsx)("span", {
														className: "integration-status is-configured",
														children: a("settings.localGhLogin")
													})] }), /* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.githubCredentials") })]
												})
											] })
										]
									})
								}),
								/* @__PURE__ */ (0, J.jsx)("div", {
									className: "settings-toggle",
									children: /* @__PURE__ */ (0, J.jsx)(wv, {
										enabled: Se && we !== "none",
										onChange: (e) => {
											Ce(e), R();
										}
									})
								})
							]
						})
					}),
					/* @__PURE__ */ (0, J.jsx)(k_, {
						title: a("heading.notifications"),
						children: /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section",
							children: [/* @__PURE__ */ (0, J.jsxs)("div", {
								className: "settings-copy",
								children: [/* @__PURE__ */ (0, J.jsx)("h4", { children: a("settings.feishuNotifications") }), /* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.notificationsDescription") })]
							}), /* @__PURE__ */ (0, J.jsx)("div", {
								className: "settings-toggle",
								children: /* @__PURE__ */ (0, J.jsx)(wv, {
									enabled: xe,
									onChange: (e) => {
										L(e), R();
									}
								})
							})]
						})
					}),
					/* @__PURE__ */ (0, J.jsx)(k_, {
						title: a("heading.variableKeys"),
						action: /* @__PURE__ */ (0, J.jsx)("span", {
							className: "muted",
							children: a("settings.storedWorkspace")
						}),
						children: /* @__PURE__ */ (0, J.jsxs)("div", {
							className: "settings-section",
							children: [/* @__PURE__ */ (0, J.jsxs)("div", {
								className: "settings-copy",
								children: [/* @__PURE__ */ (0, J.jsx)("h4", { children: a("settings.availableKeys") }), /* @__PURE__ */ (0, J.jsx)("p", { children: a("settings.availableKeysDescription") })]
							}), /* @__PURE__ */ (0, J.jsx)("div", {
								className: "settings-control wide",
								children: /* @__PURE__ */ (0, J.jsx)("div", {
									className: "secret-list",
									children: xt.length ? xt.map((e) => {
										let t = pe[e] ?? de[e] ?? "";
										return /* @__PURE__ */ (0, J.jsxs)("div", {
											className: "secret-row",
											children: [
												/* @__PURE__ */ (0, J.jsx)("code", { children: e }),
												/* @__PURE__ */ (0, J.jsx)("input", {
													type: de[e] || pe[e] !== void 0 ? "text" : "password",
													value: t,
													placeholder: a("settings.revealReplacement"),
													"aria-label": a("common.valueFor", { name: e }),
													onChange: (t) => {
														let n = t.target.value;
														me((t) => ({
															...t,
															[e]: n
														})), R();
													}
												}),
												/* @__PURE__ */ (0, J.jsxs)("div", { children: [/* @__PURE__ */ (0, J.jsx)(O_, {
													label: a("common.revealValue"),
													onClick: () => void yt(e),
													children: de[e] ? /* @__PURE__ */ (0, J.jsx)(Jh, { size: 15 }) : /* @__PURE__ */ (0, J.jsx)(Yh, { size: 15 })
												}), /* @__PURE__ */ (0, J.jsx)(O_, {
													label: a("common.copyValue"),
													onClick: () => void bt(e),
													children: /* @__PURE__ */ (0, J.jsx)(Kh, { size: 15 })
												})] })
											]
										}, e);
									}) : /* @__PURE__ */ (0, J.jsx)(W_, { label: a("common.noIntegrationKeys") })
								})
							})]
						})
					})
				]
			}),
			/* @__PURE__ */ (0, J.jsxs)("footer", {
				className: "settings-save-bar",
				children: [/* @__PURE__ */ (0, J.jsx)("span", {
					className: nt ? "settings-save-status unsaved" : "settings-save-status",
					children: a(et ? "common.saving" : nt ? "settings.unsavedChanges" : "settings.allSaved")
				}), /* @__PURE__ */ (0, J.jsxs)("button", {
					className: `button primary${et ? " is-busy" : ""}`,
					disabled: !nt || et,
					onClick: () => void Ft(),
					children: [et ? /* @__PURE__ */ (0, J.jsx)(ag, {
						size: 15,
						className: "spin"
					}) : /* @__PURE__ */ (0, J.jsx)(ug, { size: 15 }), a(et ? "common.saving" : "action.saveChanges")]
				})]
			})
		]
	});
}
function wv({ enabled: e, onChange: t }) {
	let { t: n } = Z();
	return /* @__PURE__ */ (0, J.jsxs)("label", {
		className: "schedule-toggle",
		children: [
			/* @__PURE__ */ (0, J.jsx)("input", {
				type: "checkbox",
				checked: e,
				onChange: (e) => t(e.target.checked)
			}),
			/* @__PURE__ */ (0, J.jsx)("span", { "aria-hidden": "true" }),
			/* @__PURE__ */ (0, J.jsx)("em", { children: n(e ? "common.enabled" : "common.paused") })
		]
	});
}
(0, ge.createRoot)(document.getElementById("root")).render(/* @__PURE__ */ (0, J.jsx)(zg, { children: /* @__PURE__ */ (0, J.jsx)(A_, {}) }));
//#endregion
