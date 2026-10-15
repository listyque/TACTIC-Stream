"use strict";

const useEffect = React.useEffect;
const useState = React.useState;
const useRef = React.useRef;
const Modal = MaterialUI.Modal;
const Checkbox = MaterialUI.Checkbox;
const TextField = MaterialUI.TextField;
const Menu = MaterialUI.Menu;
const MenuItem = MaterialUI.MenuItem;
const Button = MaterialUI.Button;
const IconButton = MaterialUI.IconButton;
const Tabs = MaterialUI.Tabs;
const Tab = MaterialUI.Tab;
const Box = MaterialUI.Box;
const Alert = MaterialUI.Alert;
const SimpleModal = React.forwardRef((props, ref) => {
  React.useImperativeHandle(ref, () => ({
    set_show(show) {
      set_show(show);
    },
    show() {
      set_show(true);
    },
    hide() {
      set_show(false);
    }
  }));
  const [show, set_show] = useState(false);
  const [state, set_state] = useState("normal");
  let default_width = props.width || "70vw";
  let default_height = props.height || "90vh";
  const [width, set_width] = useState(default_width);
  const [height, set_height] = useState(default_height);
  useEffect(() => {
    if (props.show) {
      set_show(props.show);
    }
  }, [props.show]);
  useEffect(() => {
    if (state == "maximize") {
      set_width("100vw");
      set_height("100vh");
    } else {
      set_width(default_width);
      set_height(default_height);
    }
  }, [state]);
  return React.createElement(Modal, {
    open: show,
    onClose: e => set_show(false)
  }, React.createElement("div", {
    className: "spt_modal",
    style: {
      width: width,
      height: height,
      padding: "10px 20px",
      background: "#F9F9F9"
    }
  }, React.createElement("div", {
    style: {
      background: "aliceblue",
      margin: "-10px -20px 20px -20px",
      padding: "10px 10px"
    }
  }, React.createElement("div", {
    style: {
      position: "absolute",
      top: "10px",
      right: "10px"
    }
  }, state == "maximize" ? React.createElement(IconButton, {
    title: "Normal",
    onClick: e => {
      set_state("normal");
    }
  }, React.createElement("i", {
    style: {
      fontSize: "1.0rem"
    },
    class: "far fa-window-restore"
  })) : React.createElement(IconButton, {
    title: "Maximize",
    onClick: e => {
      set_state("maximize");
    }
  }, React.createElement("i", {
    style: {
      fontSize: "1.0rem"
    },
    class: "far fa-window-maximize"
  })), React.createElement(IconButton, {
    onClick: e => {
      set_show(false);
    }
  }, React.createElement("i", {
    style: {
      fontSize: "1.0rem"
    },
    class: "far fa-window-close"
  }))), React.createElement("div", {
    style: {
      fontSize: "1.2rem",
      padding: "15px",
      margin: "-10px -10px 0px -10px"
    }
  }, props.title || "Title")), show == true && props.get_content ? props.get_content({}) : React.createElement("h1", null, "No Content")));
});
if (!spt.react.widget) {
  spt.react.widget = {};
}
spt.react.widget.SimpleModal = SimpleModal;