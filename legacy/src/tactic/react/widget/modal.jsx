
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



const SimpleModal = React.forwardRef( (props, ref) => {

    React.useImperativeHandle( ref, () => ({
        set_show(show) {
            set_show(show);
        },
        show() {
            set_show(true);
        },
        hide() {
            set_show(false);
        },
    }))
    const [show, set_show] = useState(false);

    const [state, set_state] = useState("normal");

    let default_width = props.width || "70vw";
    let default_height = props.height || "90vh";

    const [width, set_width] = useState(default_width)
    const [height, set_height] = useState(default_height)

    useEffect( () => {
        if (props.show) {
            set_show(props.show);
        }
    }, [props.show] )

    useEffect( () => {
        if (state == "maximize") {
            set_width("100vw");
            set_height("100vh");
        }
        else {
            set_width(default_width);
            set_height(default_height);
        }

    }, [state] )


    return (
    <Modal
       open={show}
       onClose={ e => set_show(false) }
    >
    <div
       className="spt_modal"
       style={{
           width: width,
           height: height,
           padding: "10px 20px",
           background: "#F9F9F9",
       }}
    >
        <div
           style={{
               background: "aliceblue",
               margin: "-10px -20px 20px -20px",
               padding: "10px 10px",
            }}
        >
            <div style={{position: "absolute", top: "10px", right: "10px"}}>
                { state == "maximize" ?
                <IconButton
                    title="Normal"
                    onClick={ e => {
                        set_state("normal");
                    } }
                ><i style={{fontSize: "1.0rem" }} class="far fa-window-restore"/>
                </IconButton>
                :
                <IconButton
                    title="Maximize"
                    onClick={ e => {
                        set_state("maximize")
                    } }
                ><i style={{fontSize: "1.0rem" }} class="far fa-window-maximize"/>
                </IconButton>
                }

                <IconButton
                    onClick={ e => {set_show(false)} }
                ><i style={{fontSize: "1.0rem"}} class="far fa-window-close"/></IconButton>

            </div>


            <div style={{fontSize: "1.2rem", padding: "15px",
                    margin: "-10px -10px 0px -10px"
            }}>{props.title || "Title" }</div>


        </div>
        { show == true && props.get_content ?
            props.get_content({})
            :
            <h1>No Content</h1>
        }
    </div>
    </Modal>
    )

})





if (!spt.react.widget) { spt.react.widget = {}; }
spt.react.widget.SimpleModal = SimpleModal

