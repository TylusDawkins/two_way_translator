import Nav from "@components/Nav";
import Recorder from "@components/Recorder";
import Feed from "@components/feed/Feed";

export default function Layout(props) {

  return <>
  <Nav/>
  <Recorder/>
  <Feed/>

  {props.children}
  </>;
}