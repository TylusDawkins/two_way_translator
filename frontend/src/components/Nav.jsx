import { useNavigate } from "@solidjs/router";



export default function Nav(props) {
    const navigate = useNavigate();

    const handleClick = (destination) => {
        navigate(`${destination}`);
    }

    return (
        <nav>
            <button onClick={()=>{handleClick('/')}}>Home</button>
            <button onClick={()=>{handleClick('/todos')}}>Todos</button>
        </nav>
    );
}