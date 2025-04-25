import { useNavigate } from "@solidjs/router";
import Nav from "../components/Nav";

export default function Home(props) {

    const variable = "Hello World!";
    console.log(variable);


    return <div>{variable}</div>
}