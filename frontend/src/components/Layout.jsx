import Nav from "@components/Nav";
import Recorder from "@components/Recorder";
import Feed from "@components/feed/Feed";
import LanguageSelector from "./LanguageSelector/LanguageSelector";

export default function Layout(props) {

  return <>
  <Nav/>
  <LanguageSelector/>
  <Recorder/>
  <Feed/>

  {props.children}
  </>;
}